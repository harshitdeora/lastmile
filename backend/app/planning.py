"""Pure constrained planning over graph-derived paths and a typed snapshot."""

from itertools import permutations
from time import perf_counter
from hashlib import sha256
from ortools.sat.python import cp_model
from .domain import World, Route, Leg, Plan, available_stock
from .execution import project


class Planner:
    def __init__(self, path_source):
        self.path_source = path_source

    def plan(self, w: World, override="", assume_open=False):
        start = perf_counter()
        roads = {r.id: r for r in w.roads}
        pending = sorted(
            [q for q in w.requests if q.status == "outstanding"], key=lambda q: q.id
        )
        cache = {}

        def paths(a, b):
            if (a, b) not in cache:
                cache[a, b] = self.path_source(
                    w.id, a, b, w.time, override, assume_open
                )
            return cache[a, b]

        def valid_path(a, b, time):
            for nodes, ids, cost in paths(a, b):
                entry = time
                valid = True
                for road_id in ids:
                    road = roads[road_id]
                    hypothetical = road_id == override
                    open_state = (
                        assume_open if hypothetical else road.status == "VERIFIED_OPEN"
                    )
                    until = (
                        w.time + road.inspection_validity
                        if hypothetical
                        else road.valid_until
                    )
                    if not open_state or until <= entry:
                        valid = False
                        break
                    entry += road.minutes
                if valid:
                    return nodes, ids, cost
            return None

        candidates = []
        for v in sorted(w.vehicles, key=lambda v: v.id):
            if (
                not v.available
                or v.assignment
                or (not v.loaded and v.location != v.depot)
            ):
                continue
            for size in (1, 2):
                for order in permutations(pending, size):
                    quantity = sum(q.quantity for q in order)
                    if quantity > v.capacity or (v.loaded and quantity > v.loaded):
                        continue
                    time, location = w.time, v.location
                    legs = []
                    arrivals = {}
                    for q in order:
                        path = valid_path(location, q.destination, time)
                        if path is None:
                            break
                        nodes, ids, cost = path
                        if time + cost > min(q.deadline, w.horizon):
                            break
                        if (
                            not ids
                        ):  # current location delivery requires an explicit zero-time handling leg
                            # Recovered vehicles can already be at a shelter. Hand off at current minute.
                            legs.append(
                                Leg(
                                    road="",
                                    start=location,
                                    end=location,
                                    minutes=0,
                                    request=q.id,
                                )
                            )
                        for i, road_id in enumerate(ids):
                            legs.append(
                                Leg(
                                    road=road_id,
                                    start=nodes[i],
                                    end=nodes[i + 1],
                                    minutes=roads[road_id].minutes,
                                    request=q.id if i == len(ids) - 1 else None,
                                )
                            )
                        time += cost
                        location = q.destination
                        arrivals[q.id] = time
                    else:
                        candidates.append(
                            Route(
                                vehicle=v.id,
                                depot=v.depot,
                                requests=[q.id for q in order],
                                quantity=quantity,
                                legs=legs,
                                arrivals=arrivals,
                                utility=sum(q.quantity * q.weight for q in order),
                                travel=time - w.time,
                            )
                        )
        candidates.sort(
            key=lambda c: (c.vehicle, tuple(c.requests), tuple(l.road for l in c.legs))
        )
        model = cp_model.CpModel()
        xs = [model.new_bool_var(f"route_{i}") for i in range(len(candidates))]
        for v in w.vehicles:
            model.add(sum(x for x, c in zip(xs, candidates) if c.vehicle == v.id) <= 1)
        for q in pending:
            model.add(sum(x for x, c in zip(xs, candidates) if q.id in c.requests) <= 1)
        for d in w.depots:
            model.add(
                sum(
                    x * c.quantity
                    for x, c in zip(xs, candidates)
                    if c.depot == d.id
                    and not next(v for v in w.vehicles if v.id == c.vehicle).loaded
                )
                <= max(0, available_stock(w, d.id))
            )
        # One unit of utility dominates all possible secondary objectives.
        travel_scale = len(candidates) * len(w.vehicles) + 1
        tie_bound = (
            sum(c.travel * travel_scale + i + 1 for i, c in enumerate(candidates)) + 1
        )
        model.maximize(
            sum(
                x * (c.utility * tie_bound - c.travel * travel_scale - i - 1)
                for i, (x, c) in enumerate(zip(xs, candidates))
            )
        )
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 2
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 0
        status = solver.solve(model)
        selected = [
            c
            for x, c in zip(xs, candidates)
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) and solver.value(x)
        ]
        committed = sum(
            q.quantity * q.weight
            for q in w.requests
            if q.status == "delivered" and q.delivered_at <= q.deadline
        )
        for a in w.assignments:
            if a.state in ("reserved", "in_transit"):
                committed += sum(
                    q.quantity * q.weight
                    for q in w.requests
                    if q.id in a.route.requests
                    and q.status != "delivered"
                    and a.route.arrivals.get(q.id, w.horizon + 1) <= q.deadline
                )
        served = {q for c in selected for q in c.requests}
        unmet = [
            dict(
                id=q.id,
                quantity=q.quantity,
                reason="No eligible route within deadline/capacity/stock, or displaced by higher utility",
            )
            for q in pending
            if q.id not in served
        ]
        digest = sha256(
            (
                str(w.revision) + str(w.time) + str([c.model_dump() for c in selected])
            ).encode()
        ).hexdigest()[:14]
        return Plan(
            id=f"plan-{digest}",
            revision=w.revision,
            routes=selected,
            utility=committed + sum(c.utility for c in selected),
            status=solver.status_name(status),
            solver_seconds=round(perf_counter() - start, 4),
            unmet=unmet,
        )

    def rank(self, w: World):
        base = self.plan(w)
        rankings = []
        solver_seconds = base.solver_seconds
        if w.budget <= 0 or w.time >= w.horizon:
            return {
                "base_utility": base.utility,
                "candidates": [],
                "recommendation": "Proceed without inspection",
                "revision": w.revision,
                "solver_seconds": solver_seconds,
            }
        for road in sorted(w.roads, key=lambda r: r.id):
            if (
                road.status not in ("UNKNOWN", "STALE", "CONFLICTING")
                or w.time + road.inspection_minutes > w.horizon
            ):
                continue
            projected = project(w, road.inspection_minutes)
            projected.budget -= 1
            # Both branches use identical time and observed-only fleet projection.
            opened = self.plan(projected, road.id, True)
            closed = self.plan(projected, road.id, False)
            solver_seconds += opened.solver_seconds + closed.solver_seconds
            expected = road.prior * opened.utility + (1 - road.prior) * closed.utility
            affected = sorted(
                {
                    q
                    for p in (opened, closed)
                    for route in p.routes
                    for q in route.requests
                }
            )
            rankings.append(
                dict(
                    road=road.id,
                    name=road.name,
                    prior=road.prior,
                    prior_source=road.prior_source,
                    minutes=road.inspection_minutes,
                    open_utility=opened.utility,
                    closed_utility=closed.utility,
                    expected_utility=round(expected, 3),
                    gain=round(expected - base.utility, 3),
                    affected_requests=affected,
                    evidence_ids=[road.id]
                    + [r.id for r in w.reports if r.road == road.id],
                    branch_solver_status=[opened.status, closed.status],
                )
            )
            if len(rankings) >= 4:
                break
        rankings.sort(key=lambda c: (-c["gain"], c["road"]))
        return dict(
            base_utility=base.utility,
            candidates=rankings,
            revision=w.revision,
            solver_seconds=round(solver_seconds, 4),
            recommendation=(
                f"Inspect {rankings[0]['road']}"
                if rankings and rankings[0]["gain"] > 0
                else "Proceed without inspection"
            ),
            limits="One-step estimate; maximum 4 candidate roads; same bounded planner in every branch",
        )
