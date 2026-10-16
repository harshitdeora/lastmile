import json
from threading import RLock
from uuid import uuid4
from .domain import Assignment, Reservation, Inspection, Decision, available_stock
from .graph import GraphStore, Conflict
from .scenarios import observed_world
from .simulator import Simulator
from .planning import Planner
from .execution import advance_world, observe, invalidate


class Operations:
    def __init__(self, store=None, simulator=None):
        self.store = store or GraphStore()
        self.simulator = simulator or Simulator()
        self.planner = Planner(self.store.paths)
        self.lock = (
            RLock()
        )  # single-process MVP; process lease enforced by API lifespan

    def create(self, scenario, seed=0, budget=2):
        with self.lock:
            self.store.health()
            run_id = uuid4().hex
            w = observed_world(run_id, scenario)
            if not 0 <= budget <= 4:
                raise ValueError("Inspection budget must be between 0 and 4")
            w.budget = budget
            self.simulator.create(run_id, scenario, seed)
            self.store.save(w, -1, initial=True)
            return self.context(run_id)

    def context(self, run_id):
        with self.lock:
            w = self.store.load(run_id)
            data = w.model_dump(exclude={"idempotency"})
            data["metrics"] = w.calculate_metrics()
            data["stock_available"] = {d.id: available_stock(w, d.id) for d in w.depots}
            data["synthetic"] = True
            return data

    def mutate(self, run_id, operation, key, callback):
        if not key or len(key) > 128:
            raise ValueError("An idempotency key of 1–128 characters is required")
        with self.lock:
            w = self.store.load(run_id)
            if key in w.idempotency:
                previous = w.idempotency[key]
                if previous["operation"] != operation:
                    raise Conflict("Idempotency key belongs to another operation")
                return previous["response"]
            expected = w.revision
            result = callback(w)
            w.revision += 1
            response = dict(result or {}, revision=w.revision)
            if len(w.idempotency) >= 1000:
                raise Conflict("Run action limit reached; create a new run")
            w.idempotency[key] = {"operation": operation, "response": response}
            self.store.save(w, expected)
            return response

    def rank(self, run_id):
        with self.lock:
            return self.planner.rank(self.store.load(run_id))

    def preview(self, run_id):
        with self.lock:
            return self.planner.plan(self.store.load(run_id)).model_dump()

    def impact(self, run_id, road):
        with self.lock:
            w = self.store.load(run_id)
            if road not in {r.id for r in w.roads}:
                raise ValueError("Unknown road")
            result = self.store.query(run_id, "impact", {"road": road})
            # Hypothetical routes complement active-assignment dependencies.
            hypothetical = self.planner.plan(w, road, True)
            requests = sorted(
                {
                    q
                    for route in hypothetical.routes
                    if any(l.road == road for l in route.legs)
                    for q in route.requests
                }
            )
            return dict(
                revision=w.revision,
                road=road,
                graph_rows=result,
                hypothetical_requests=requests,
                reports=[r.model_dump() for r in w.reports if r.road == road],
            )

    def inspect(self, run_id, road, key):
        def action(w):
            if w.status != "active":
                raise Conflict("Run is complete")
            r = next((r for r in w.roads if r.id == road), None)
            if not r:
                raise ValueError("Unknown road")
            if r.status not in ("UNKNOWN", "STALE", "CONFLICTING"):
                raise Conflict("Road already has valid authoritative evidence")
            if w.budget <= 0 or w.time + r.inspection_minutes > w.horizon:
                raise Conflict("Insufficient budget or simulation time")
            cost = r.inspection_minutes
            advance_world(w, w.time + cost, self.simulator)
            result = "OPEN" if self.simulator.is_open(w.id, road, w.time) else "CLOSED"
            report = observe(w, road, result, w.time, w.time)
            inspection = Inspection(
                id=f"inspection-{len(w.inspections)+1}",
                road=road,
                result=result,
                observed_at=w.time,
                minutes=cost,
            )
            w.inspections.append(inspection)
            w.budget -= 1
            self._decision(
                w,
                "Manual inspection",
                f"Inspected {road}: {result.lower()} at minute {w.time}.",
                [road, inspection.id, report.id],
            )
            return {"inspection": inspection.model_dump()}

        return self.mutate(run_id, "inspect:" + road, key, action)

    def commit(self, run_id, plan_id, revision, key):
        def action(w):
            if w.status != "active":
                raise Conflict("Run is complete")
            if w.revision != revision:
                raise Conflict("Stale plan revision; refresh and preview again")
            plan = self.planner.plan(w)
            if plan.id != plan_id:
                raise Conflict("Plan changed; preview again")
            if not plan.routes:
                raise Conflict("No new deliveries can be reserved by this plan")
            w.plans.append(plan)
            w.replans += 1
            for route in plan.routes:
                v = next(v for v in w.vehicles if v.id == route.vehicle)
                a = Assignment(
                    id="assignment-" + uuid4().hex[:12], plan=plan.id, route=route
                )
                w.assignments.append(a)
                v.assignment = a.id
                allocation = 0 if v.loaded else route.quantity
                if allocation > available_stock(w, route.depot):
                    raise Conflict("Stock changed")
                w.reservations.append(
                    Reservation(
                        id="reservation-" + a.id,
                        assignment=a.id,
                        depot=route.depot,
                        quantity=allocation,
                    )
                )
                for q in w.requests:
                    if q.id in route.requests:
                        q.status = "reserved"
            w.event(
                "reservation",
                f"Reserved {len(plan.routes)} vehicle routes; stock held until loading.",
                [plan.id],
            )
            self._decision(
                w,
                "Planner",
                f"Reserved plan with predicted utility {plan.utility}.",
                [plan.id] + [q for c in plan.routes for q in c.requests],
                plan.id,
            )
            return {"plan": plan.model_dump()}

        return self.mutate(run_id, "commit:" + plan_id, key, action)

    def advance(self, run_id, minutes, key):
        if not 1 <= minutes <= 180:
            raise ValueError("Advance minutes must be between 1 and 180")

        def action(w):
            if w.time >= w.horizon:
                raise Conflict("Simulation horizon reached")
            advance_world(w, w.time + minutes, self.simulator)
            w.event("clock", f"Simulation advanced to minute {w.time}.")
            return {"time": w.time, "metrics": w.calculate_metrics()}

        return self.mutate(run_id, "advance:" + str(minutes), key, action)

    def disrupt(self, run_id, key):
        def action(w):
            v = next((v for v in w.vehicles if v.available and v.loaded == 0), None)
            if not v:
                raise Conflict("No unloaded available vehicle can be withdrawn")
            v.available = False
            for a in w.assignments:
                if a.route.vehicle == v.id and a.state == "reserved":
                    invalidate(
                        w, a, "Scripted withdrawal released unstarted reservation"
                    )
            w.event(
                "capacity",
                f"Scripted disruption: {v.name} unavailable; loaded work preserved.",
                [v.id],
            )
            return {"vehicle": v.id}

        return self.mutate(run_id, "disrupt", key, action)

    def _decision(self, w, mode, summary, evidence, plan=None, calls=None):
        w.decisions.append(
            Decision(
                id=f"decision-{len(w.decisions)+1}",
                time=w.time,
                mode=mode,
                summary=summary,
                evidence=evidence,
                plan=plan,
                calls=calls or [],
            )
        )

    def record_controller(self, run_id, mode, summary, evidence, calls):
        def action(w):
            if w.cycles >= 30:
                raise Conflict("Controller cycle limit reached")
            w.cycles += 1
            self._decision(w, mode, summary, evidence, calls=calls)

        return self.mutate(run_id, "controller_record", uuid4().hex, action)

    def deterministic_cycle(self, run_id, policy="value", rng=None):
        w = self.store.load(run_id)
        if w.status != "active" or w.cycles >= 30:
            return {"stopped": True, "reason": "Run complete or 30-cycle bound reached"}
        calls = []
        evidence = []
        ranking = self.rank(run_id)
        calls.append({"tool": "rank_inspections", "result": ranking})
        chosen = None
        eligible = ranking["candidates"]
        if policy == "value" and eligible and eligible[0]["gain"] > 0:
            chosen = eligible[0]
        elif policy == "random" and eligible:
            chosen = rng.choice(eligible)
        if chosen:
            result = self.inspect(run_id, chosen["road"], uuid4().hex)
            calls.append(
                {
                    "tool": "inspect_road",
                    "arguments": {"road": chosen["road"]},
                    "result": result,
                }
            )
            evidence.extend(chosen["evidence_ids"] + [result["inspection"]["id"]])
        plan = self.preview(run_id)
        calls.append({"tool": "propose_delivery_plan", "result": plan})
        if plan["routes"]:
            result = self.commit(run_id, plan["id"], plan["revision"], uuid4().hex)
            calls.append({"tool": "commit_delivery_plan", "result": result})
            evidence.append(plan["id"])
        result = self.advance(run_id, 10, uuid4().hex)
        calls.append({"tool": "advance_simulation", "result": result})
        summary = (
            (
                f"Inspected {chosen['road']}"
                if chosen
                else "Proceeded without inspection"
            )
            + f"; planned utility {plan['utility']}; advanced simulation by up to 10 minutes."
        )
        self.record_controller(run_id, "Deterministic demo", summary, evidence, calls)
        return {"mode": "Deterministic demo", "summary": summary, "calls": calls}

    def replay(self, run_id):
        from .domain import World

        snapshots = []
        for rev, time, data in self.store.query(run_id, "replay"):
            world = World.model_validate_json(data)
            state = world.model_dump(exclude={"idempotency"})
            state.update(
                metrics=world.calculate_metrics(),
                stock_available={
                    d.id: available_stock(world, d.id) for d in world.depots
                },
            )
            snapshots.append(dict(revision=rev, time=time, state=state))
        return snapshots

    def evidence(self, run_id, decision):
        w = self.store.load(run_id)
        return {
            "revision": w.revision,
            "decision": next(
                (d.model_dump() for d in w.decisions if d.id == decision), None
            ),
            "graph": self.store.query(run_id, "decision", {"decision": decision}),
        }
