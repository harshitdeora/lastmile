"""Shared explicit-time event loop for real execution and observed-only projection."""

from .domain import World, Report


def invalidate(w: World, assignment, reason: str):
    vehicle = next(v for v in w.vehicles if v.id == assignment.route.vehicle)
    if assignment.state == "reserved":
        assignment.state = "cancelled"
        for reservation in w.reservations:
            if reservation.assignment == assignment.id:
                reservation.state = "released"
    else:
        assignment.state = "blocked"
    vehicle.assignment = None
    for q in w.requests:
        if q.id in assignment.route.requests and q.status != "delivered":
            q.status = "outstanding"
    w.event(assignment.state, reason, [assignment.id, vehicle.id])


def observe(
    w: World,
    road_id: str,
    result: str,
    at: int,
    received: int,
    source="Inspection",
    authority="inspection",
):
    road = next(r for r in w.roads if r.id == road_id)
    report = Report(
        id=f"report-{len(w.reports)+1}",
        road=road_id,
        claim=result,
        source=source,
        authority=authority,
        observed_at=at,
        received_at=received,
        text=f"{source}: {result} at simulation minute {at}.",
    )
    w.reports.append(report)
    if authority in ("inspection", "traversal") and at >= road.observed_at:
        road.status = "VERIFIED_OPEN" if result == "OPEN" else "VERIFIED_CLOSED"
        road.observed_at, road.valid_until = at, at + road.inspection_validity
    elif (
        authority == "unverified"
        and at > road.observed_at
        and road.status not in ("VERIFIED_OPEN", "VERIFIED_CLOSED")
    ):
        road.status = "CONFLICTING"
    w.event(
        "observation",
        f"{road.name}: {result.lower()} observation received.",
        [report.id, road_id],
    )
    return report


def advance_world(w: World, target: int, simulator=None):
    roads = {r.id: r for r in w.roads}
    vehicles = {v.id: v for v in w.vehicles}
    requests = {q.id: q for q in w.requests}
    for time in range(w.time, min(target, w.horizon) + 1):
        w.time = time
        if simulator:
            for e in simulator.delivered_events(w.id, time):
                event_id = f"withdrawal-{e['id']}-{e['time']}"
                if not any(event_id in x.ids for x in w.events):
                    v = vehicles[e["id"]]
                    v.available = False
                    w.event(
                        "capacity",
                        f"{v.name} withdrawn from new work. Entered segments and loaded work finish.",
                        [v.id, event_id],
                    )
                    for a in w.assignments:
                        if a.route.vehicle == v.id and a.state == "reserved":
                            invalidate(w, a, "Vehicle unavailable before dispatch")
        for road in w.roads:
            if road.status.startswith("VERIFIED") and road.valid_until <= time:
                road.status = "STALE"
                w.event("expiry", f"Verification expired for {road.name}.", [road.id])
        for a in w.assignments:
            if a.state not in ("reserved", "in_transit"):
                continue
            v = vehicles[a.route.vehicle]
            if a.state == "reserved":
                entry = time
                valid = True
                for leg in a.route.legs:
                    if not leg.road:
                        continue
                    road = roads[leg.road]
                    if road.status != "VERIFIED_OPEN" or road.valid_until <= entry:
                        valid = False
                    entry += leg.minutes
                if not v.available or not valid:
                    invalidate(
                        w,
                        a,
                        "Unstarted route invalidated by availability or evidence expiry",
                    )
                    continue
                # Loading is the physical stock handoff. Existing onboard kits are reused first.
                for reservation in w.reservations:
                    if reservation.assignment == a.id:
                        v.loaded += reservation.quantity
                        reservation.state = "loaded"
                a.state = "in_transit"
                w.event("dispatch", f"{v.name} loaded and dispatched.", [a.id, v.id])
            if a.exits_at is not None and time >= a.exits_at:
                leg = a.route.legs[a.index]
                v.location = leg.end
                if leg.request and requests[leg.request].status != "delivered":
                    q = requests[leg.request]
                    q.status, q.delivered_at = "delivered", time
                    v.loaded -= q.quantity
                    w.event(
                        "delivery",
                        f"{q.quantity} relief kits delivered to {q.destination.upper()}"
                        + (" on time." if time <= q.deadline else " after deadline."),
                        [q.id, a.id, v.id],
                    )
                a.index += 1
                a.entered_at = a.exits_at = None
            while a.index < len(a.route.legs) and not a.route.legs[a.index].road:
                leg = a.route.legs[a.index]
                q = requests[leg.request]
                if q.status != "delivered":
                    q.status, q.delivered_at = "delivered", time
                    v.loaded -= q.quantity
                    w.event(
                        "delivery",
                        f"{q.quantity} relief kits handed off at current location.",
                        [q.id, a.id, v.id],
                    )
                a.index += 1
            if a.index >= len(a.route.legs):
                a.state = "delivered"
                v.assignment = None
                for r in w.reservations:
                    if r.assignment == a.id:
                        r.state = "consumed"
                continue
            if a.entered_at is None:
                leg = a.route.legs[a.index]
                road = roads[leg.road]
                if road.status != "VERIFIED_OPEN" or road.valid_until <= time:
                    invalidate(
                        w,
                        a,
                        "Next segment lacks valid open evidence; loaded inventory retained",
                    )
                    continue
                if simulator and not simulator.is_open(w.id, road.id, time):
                    w.failed_traversals += 1
                    observe(
                        w, road.id, "CLOSED", time, time, "Traversal check", "traversal"
                    )
                    invalidate(
                        w,
                        a,
                        "Physical closure prevented entry; current position and loaded inventory retained",
                    )
                    continue
                a.entered_at, a.exits_at = time, time + leg.minutes
    if w.time >= w.horizon or all(q.status == "delivered" for q in w.requests):
        w.status = "complete"
    return w


def project(w: World, minutes: int):
    """No truth argument: projections can only consume current observations."""
    return advance_world(w.model_copy(deep=True), w.time + minutes)
