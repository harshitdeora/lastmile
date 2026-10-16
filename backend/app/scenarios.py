"""Public scenario generation. Seed never enters World or public DTOs."""

from .domain import World, Location, Road, Request, Depot, Vehicle, Report

CATALOGUE = [
    {
        "id": "critical_crossing",
        "name": "Critical crossing",
        "description": "Conflicting bridge reports, urgent eastern shelters and a long verified detour.",
    },
    {
        "id": "capacity_disruption",
        "name": "Capacity disruption",
        "description": "The same crossing, with a time-scheduled vehicle withdrawal and explicit recovery.",
    },
    {
        "id": "no_useful_inspection",
        "name": "No useful inspection",
        "description": "Inspection delay exceeds urgent delivery windows. Keep the budget.",
    },
]


def observed_world(run_id: str, scenario: str) -> World:
    if scenario not in {s["id"] for s in CATALOGUE}:
        raise ValueError("Unknown scenario")
    specs = [
        ("d1", "North depot", "depot", 110, 100),
        ("d2", "West depot", "depot", 90, 330),
        ("d3", "South depot", "depot", 200, 540),
        ("j1", "Orchard", "junction", 245, 100),
        ("j2", "Market", "junction", 260, 250),
        ("j3", "Quarry", "junction", 290, 430),
        ("j4", "West bank", "junction", 395, 250),
        ("j5", "East bank", "junction", 535, 250),
        ("j6", "Ridge", "junction", 470, 80),
        ("j7", "Marsh", "junction", 470, 510),
        ("j8", "Old ferry", "junction", 640, 420),
        ("s1", "Hill school", "shelter", 680, 100),
        ("s2", "Civic hall", "shelter", 720, 250),
        ("s3", "Riverside", "shelter", 760, 420),
        ("s4", "Garden centre", "shelter", 130, 200),
        ("s5", "South camp", "shelter", 360, 570),
    ]
    edges = [
        ("d1", "j1", 7),
        ("j1", "j2", 7),
        ("d2", "j2", 8),
        ("d2", "s4", 6),
        ("d1", "s4", 7),
        ("s4", "j2", 8),
        ("j2", "j4", 5),
        ("j4", "j5", 4),
        ("j5", "s1", 9),
        ("j5", "s2", 6),
        ("j5", "j8", 8),
        ("j8", "s3", 5),
        ("j1", "j6", 25),
        ("j6", "s1", 25),
        ("j4", "j6", 28),
        ("s1", "s2", 9),
        ("s2", "s3", 10),
        ("j2", "j3", 10),
        ("d3", "j3", 7),
        ("d3", "s5", 8),
        ("j3", "s5", 9),
        ("j3", "j7", 24),
        ("j7", "j8", 22),
        ("j7", "s5", 20),
        ("j3", "j4", 9),
    ]
    roads = [
        Road(
            id=f"r{i+1:02}",
            name="Alder bridge" if i == 7 else f"{a.upper()} · {b.upper()}",
            a=a,
            b=b,
            minutes=t,
        )
        for i, (a, b, t) in enumerate(edges)
    ]
    bridge = roads[7]
    bridge.status, bridge.valid_until = "CONFLICTING", 0
    bridge.inspection_minutes = 45 if scenario == "no_useful_inspection" else 5
    roads[21].status, roads[21].valid_until = "STALE", 0
    roads[21].inspection_minutes, roads[21].prior = 18, 0.35
    requests = [
        Request(id=f"q{i+1}", destination=s, quantity=q, deadline=d, weight=p)
        for i, (s, q, d, p) in enumerate(
            [
                ("s1", 8, 42, 3),
                ("s2", 10, 34, 4),
                ("s3", 8, 48, 3),
                ("s4", 6, 30, 2),
                ("s5", 6, 40, 2),
                ("s2", 4, 75, 1),
            ]
        )
    ]
    reports = [
        Report(
            id="report-bridge-1",
            road="r08",
            claim="OPEN",
            source="Volunteer radio",
            observed_at=-8,
            received_at=0,
            text="Crossing looks clear; not physically checked.",
        ),
        Report(
            id="report-bridge-2",
            road="r08",
            claim="CLOSED",
            source="Neighbourhood message",
            observed_at=-5,
            received_at=0,
            text="Water reported across the eastern approach.",
        ),
        Report(
            id="report-marsh",
            road="r22",
            claim="OPEN",
            source="Previous shift",
            observed_at=-90,
            received_at=-70,
            text="Old report; verification has expired.",
        ),
    ]
    w = World(
        id=run_id,
        scenario=scenario,
        locations=[Location(id=i, name=n, kind=k, x=x, y=y) for i, n, k, x, y in specs],
        roads=roads,
        requests=requests,
        depots=[
            Depot(id="d1", stock=20),
            Depot(id="d2", stock=22),
            Depot(id="d3", stock=14),
        ],
        vehicles=[
            Vehicle(id=i, name=n, depot=d, location=d, capacity=c)
            for i, n, d, c in [
                ("v1", "Orchid 01", "d1", 14),
                ("v2", "Orchid 02", "d2", 16),
                ("v3", "Orchid 03", "d2", 12),
                ("v4", "Orchid 04", "d3", 12),
            ]
        ],
        reports=reports,
    )
    w.event("created", "Fictional Alder Reach run created. All actions are simulated.")
    return w
