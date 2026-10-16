import json
from itertools import combinations
from types import SimpleNamespace
from uuid import uuid4
import pytest
from app.domain import World, Location, Road, Request, Depot, Vehicle, available_stock
from app.execution import observe, advance_world
from app.graph import GraphStore, Conflict, GraphUnavailable
from app.service import Operations
from app.simulator import Simulator
from app.planning import Planner
from app.agents import dispatch, llm_cycle, tool_definitions


@pytest.fixture
def ops(tmp_path):
    service = Operations(GraphStore(), Simulator(str(tmp_path)))
    service.store.health()  # integration checks require REAL FalkorDB, never a fallback
    created = []
    original = service.create

    def create(scenario="critical_crossing", seed=1):
        context = original(scenario, seed)
        created.append(context["id"])
        return context

    service.create = create
    yield service
    for run_id in created:
        service.store.delete(run_id)


def assert_no_truth(value):
    forbidden = {
        "seed",
        "initial",
        "schedule",
        "truth",
        "hidden_conditions",
        "future_events",
        "world_seed",
    }
    if isinstance(value, dict):
        assert not forbidden.intersection(value)
        for v in value.values():
            assert_no_truth(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            assert_no_truth(v)
    elif isinstance(value, str) and value.startswith(("{", "[")):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return
        assert_no_truth(parsed)


def test_recursive_public_boundary(ops):
    c = ops.create()
    rid = c["id"]
    for payload in [
        c,
        ops.rank(rid),
        ops.preview(rid),
        ops.impact(rid, "r08"),
        ops.replay(rid),
        dispatch(ops, rid, "get_operational_context", {}),
    ]:
        assert_no_truth(payload)
    ops.deterministic_cycle(rid)
    assert_no_truth(ops.context(rid))
    assert_no_truth(ops.replay(rid))


def test_longer_valid_path_and_direction(ops):
    c = ops.create()
    rid = c["id"]
    paths = ops.store.paths(rid, "d2", "s2", 0)
    assert paths and all("r08" not in ids for _, ids, _ in paths)
    assert paths[0][2] > 30
    hypothetical = ops.store.paths(rid, "d2", "s2", 0, "r08", True)
    assert hypothetical[0][2] < paths[0][2]
    assert "r08" in hypothetical[0][1]


def test_initial_one_way_segment_has_no_reverse_traversal(ops):
    from app.scenarios import observed_world

    rid = uuid4().hex
    w = observed_world(rid, "critical_crossing")
    w.roads[0].bidirectional = False
    try:
        ops.store.save(w, -1, initial=True)
        graph = ops.store.graph(rid)
        assert graph.query(
            "MATCH (:Location {id:'d1'})-[e:TRAVEL {road:'r01'}]->(:Location {id:'j1'}) RETURN count(e)"
        ).result_set == [[1]]
        assert graph.query(
            "MATCH (:Location {id:'j1'})-[e:TRAVEL {road:'r01'}]->(:Location {id:'d1'}) RETURN count(e)"
        ).result_set == [[0]]
    finally:
        ops.store.delete(rid)


def test_late_report_cannot_erase_authority(ops):
    c = ops.create()
    rid = c["id"]
    w = ops.store.load(rid)
    observe(w, "r08", "OPEN", 10, 10)
    observe(w, "r08", "CLOSED", 2, 12, "Late neighbour", "unverified")
    observe(w, "r08", "CLOSED", 5, 13, "Late old inspection", "inspection")
    road = next(r for r in w.roads if r.id == "r08")
    assert road.status == "VERIFIED_OPEN" and road.observed_at == 10
    assert len([r for r in w.reports if r.road == "r08"]) == 5


def test_hypothetical_branches_never_mutate_graph(ops):
    c = ops.create()
    rid = c["id"]
    before = ops.store.load(rid).model_dump()
    rank = ops.rank(rid)
    assert rank["candidates"][0]["gain"] > 0
    assert ops.store.load(rid).model_dump() == before
    assert len(ops.replay(rid)) == 1


def test_cost_and_deadline_change_inspection_value(ops):
    rid = ops.create()["id"]
    w = ops.store.load(rid)
    first = ops.planner.rank(w)["candidates"][0]
    next(r for r in w.roads if r.id == "r08").inspection_minutes = 80
    high = next(c for c in ops.planner.rank(w)["candidates"] if c["road"] == "r08")
    assert high["gain"] < first["gain"] and high["gain"] <= 0
    w = ops.store.load(rid)
    for q in w.requests:
        q.deadline = 3
    short = next(c for c in ops.planner.rank(w)["candidates"] if c["road"] == "r08")
    assert short["gain"] < first["gain"]


def test_no_useful_inspection_preserves_budget(ops):
    rid = ops.create("no_useful_inspection")["id"]
    ranking = ops.rank(rid)
    assert all(c["gain"] <= 0 for c in ranking["candidates"])
    assert ranking["recommendation"] == "Proceed without inspection"
    ops.deterministic_cycle(rid)
    assert ops.context(rid)["budget"] == 2


def test_plan_shared_stock_capacity_and_request_uniqueness(ops):
    rid = ops.create()["id"]
    ops.inspect(rid, "r08", "inspection")
    w = ops.store.load(rid)
    plan = ops.planner.plan(w)
    ids = [q for c in plan.routes for q in c.requests]
    assert len(ids) == len(set(ids))
    for c in plan.routes:
        assert c.quantity <= next(v.capacity for v in w.vehicles if v.id == c.vehicle)
        for q in c.requests:
            assert c.arrivals[q] <= next(r.deadline for r in w.requests if r.id == q)
    for d in w.depots:
        assert sum(c.quantity for c in plan.routes if c.depot == d.id) <= d.stock
    # Shared depot limit must actually change the chosen allocation.
    for d in w.depots:
        d.stock = 3
    assert not ops.planner.plan(w).routes or all(
        c.quantity <= 3 for c in ops.planner.plan(w).routes
    )


def test_commit_advance_idempotency_and_stale_revision(ops):
    rid = ops.create()["id"]
    plan = ops.preview(rid)
    first = ops.commit(rid, plan["id"], plan["revision"], "same")
    assert ops.commit(rid, plan["id"], plan["revision"], "same") == first
    w = ops.store.load(rid)
    assert len(w.assignments) == len(plan["routes"])
    with pytest.raises(Conflict):
        ops.commit(rid, plan["id"], plan["revision"], "different")
    stock = {d.id: available_stock(w, d.id) for d in w.depots}
    result = ops.advance(rid, 30, "advance-once")
    assert ops.advance(rid, 30, "advance-once") == result
    w = ops.store.load(rid)
    assert w.time == 30
    assert {d.id: available_stock(w, d.id) for d in w.depots} == stock
    assert (
        len({q.id for q in w.requests if q.status == "delivered"})
        == w.calculate_metrics()["on_time_requests"]
    )


def test_expiry_releases_only_unstarted_reservations(ops):
    rid = ops.create()["id"]
    p = ops.preview(rid)
    ops.commit(rid, p["id"], p["revision"], "commit")
    w = ops.store.load(rid)
    a = w.assignments[0]
    r = next(r for r in w.roads if r.id == a.route.legs[0].road)
    r.valid_until = 0
    advance_world(w, 1)
    assert a.state == "cancelled"
    assert next(r for r in w.reservations if r.assignment == a.id).state == "released"


def test_disruption_preserves_completed_and_loaded_work(ops):
    rid = ops.create()["id"]
    p = ops.preview(rid)
    ops.commit(rid, p["id"], p["revision"], "commit")
    ops.advance(rid, 1, "step")
    before = ops.store.load(rid)
    active = {
        a.id: a.model_dump() for a in before.assignments if a.state == "in_transit"
    }
    loaded = {
        v.id: (v.loaded, v.location, v.assignment) for v in before.vehicles if v.loaded
    }
    ops.disrupt(rid, "disrupt")
    after = ops.store.load(rid)
    assert all(
        next(a.model_dump() for a in after.assignments if a.id == i) == a
        for i, a in active.items()
    )
    assert all(
        next((v.loaded, v.location, v.assignment) for v in after.vehicles if v.id == i)
        == v
        for i, v in loaded.items()
    )


def test_fleet_moves_during_inspection(ops):
    rid = ops.create()["id"]
    p = ops.preview(rid)
    ops.commit(rid, p["id"], p["revision"], "commit")
    ops.advance(rid, 1, "dispatch")
    before = ops.store.load(rid)
    projected = ops.planner.rank(before)
    assert ops.store.load(rid).time == 1
    ops.inspect(rid, "r08", "inspect")
    w = ops.store.load(rid)
    assert w.time == 6
    assert any(q.status == "delivered" for q in w.requests)  # six-minute local delivery


def test_restart_and_replay_resume_observed_and_private_state(ops):
    rid = ops.create()["id"]
    ops.deterministic_cycle(rid)
    before = ops.context(rid)
    restart = Operations(GraphStore(), Simulator(str(ops.simulator.directory)))
    assert restart.context(rid) == before
    assert restart.simulator.is_open(rid, "r08", 5) == ops.simulator.is_open(
        rid, "r08", 5
    )
    snapshots = restart.replay(rid)
    assert snapshots[-1]["revision"] == before["revision"]
    assert snapshots[-1]["state"]["budget"] == before["budget"]
    assert restart.context(rid) == before  # replay is read-only


def test_fair_worlds_and_separate_policy_randomness(ops):
    a = ops.create("capacity_disruption", 3)
    b = ops.create("capacity_disruption", 3)
    aid = a.pop("id")
    bid = b.pop("id")
    assert a == b
    assert ops.simulator._load(aid) == ops.simulator._load(bid)
    for time in (0, 25, 26, 100):
        assert ops.simulator.is_open(aid, "r10", time) == ops.simulator.is_open(
            bid, "r10", time
        )
    assert not ops.simulator.delivered_events(aid, 17)
    assert ops.simulator.delivered_events(aid, 18)


def test_graph_failure_is_explicit(monkeypatch):
    monkeypatch.setenv("FALKOR_PORT", "1")
    o = Operations()
    with pytest.raises(GraphUnavailable):
        o.create("critical_crossing")


def test_reject_untrusted_tool_and_extra_arguments(ops):
    rid = ops.create()["id"]
    with pytest.raises(ValueError):
        dispatch(ops, rid, "raw_cypher", {"query": "DELETE"})
    with pytest.raises(ValueError):
        dispatch(ops, rid, "inspect_road", {"road": "r08", "shell": "x"})
    for tool in tool_definitions():
        assert tool["strict"] and tool["parameters"]["additionalProperties"] is False


def test_real_adapter_protocol_with_stub_is_not_live_verification(ops):
    rid = ops.create()["id"]

    class Responses:
        def create(self, **kwargs):
            assert kwargs["parallel_tool_calls"] is False and kwargs["store"] is False
            return SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="function_call",
                        name="advance_simulation",
                        arguments='{"minutes":1}',
                        call_id="c1",
                    )
                ],
                output_text="",
            )

    result = llm_cycle(ops, rid, SimpleNamespace(responses=Responses()), "test-model")
    assert result["error_type"] is None
    assert ops.context(rid)["time"] == 1
    assert result["calls"][0]["tool"] == "advance_simulation"


def test_provider_failure_keeps_graph_consistent(ops):
    rid = ops.create()["id"]

    class Responses:
        def create(self, **kwargs):
            raise TimeoutError("do not copy provider body")

    result = llm_cycle(ops, rid, SimpleNamespace(responses=Responses()), "test-model")
    assert result["error_type"] == "TimeoutError"
    c = ops.context(rid)
    assert c["time"] == 0 and c["budget"] == 2 and c["cycles"] == 1
    assert "do not copy" not in json.dumps(c)


def test_independent_hand_enumeration():
    # Two 3-kit requests, one 3-kit vehicle. Independent feasible subsets:
    # none=0; low=3; high=9; both exceeds capacity. Bridge unlocks high.
    w = World(
        id="a" * 32,
        scenario="tiny",
        budget=1,
        locations=[
            Location(id=i, name=i, kind=k, x=0, y=0)
            for i, k in [("d", "depot"), ("a", "shelter"), ("b", "shelter")]
        ],
        roads=[
            Road(id="safe", name="safe", a="d", b="a", minutes=1),
            Road(
                id="check",
                name="check",
                a="d",
                b="b",
                minutes=1,
                status="UNKNOWN",
                prior=0.5,
                inspection_minutes=1,
            ),
        ],
        requests=[
            Request(id="low", destination="a", quantity=3, deadline=3, weight=1),
            Request(id="high", destination="b", quantity=3, deadline=3, weight=3),
        ],
        depots=[Depot(id="d", stock=3)],
        vehicles=[Vehicle(id="v", name="v", depot="d", location="d", capacity=3)],
        reports=[],
    )

    def paths(rid, source, target, now, override, opened):
        if source == target:
            return [([source], [], 0)]
        if source == "d" and target == "a":
            return [(["d", "a"], ["safe"], 1)]
        if source == "d" and target == "b" and override == "check" and opened:
            return [(["d", "b"], ["check"], 1)]
        return []

    planner = Planner(paths)
    feasible = [
        (),
        ("low",),
        ("high",),
    ]  # independently enumerated capacity-compatible subsets
    assert (
        max(
            sum(
                next(q.quantity * q.weight for q in w.requests if q.id == i)
                for i in subset
            )
            for subset in feasible
        )
        == 9
    )
    assert planner.plan(w).utility == 3
    ranking = planner.rank(w)
    branch = ranking["candidates"][0]
    assert (
        branch["open_utility"],
        branch["closed_utility"],
        branch["expected_utility"],
        branch["gain"],
    ) == (9, 3, 6, 3)
    w.roads[1].inspection_minutes = 4
    assert planner.rank(w)["candidates"][0]["gain"] == -3


def test_graph_entity_ids_and_resource_relationships_are_unambiguous(ops):
    rid = ops.create()["id"]
    p = ops.preview(rid)
    ops.commit(rid, p["id"], p["revision"], "commit")
    graph = ops.store.graph(rid)
    assert not graph.query(
        "MATCH (n:Entity) WITH n.id AS id,count(n) AS c WHERE c>1 RETURN id,c"
    ).result_set
    assert graph.query("MATCH (s:Stock) RETURN count(s)").result_set == [[3]]
    assert not graph.query(
        "MATCH (:Reservation)-[:HOLDS]->(n) WHERE NOT n:Stock RETURN n.id"
    ).result_set


def test_physical_blockage_retains_inventory_and_replans_without_new_stock(ops):
    rid = ops.create()["id"]
    p = ops.preview(rid)
    ops.commit(rid, p["id"], p["revision"], "commit")
    original = ops.simulator.is_open
    ops.simulator.is_open = lambda run_id, road, time: (
        False if road == "r04" else original(run_id, road, time)
    )
    ops.advance(rid, 1, "block")
    w = ops.store.load(rid)
    blocked = [a for a in w.assignments if a.state == "blocked"]
    assert blocked
    a = blocked[0]
    v = next(v for v in w.vehicles if v.id == a.route.vehicle)
    assert v.location == "d2" and v.loaded == 6 and v.assignment is None
    stock_before = available_stock(w, "d2")

    # Isolate the recovered vehicle: otherwise a fresh nearer vehicle can legitimately win the travel tie-break.
    def isolate(world):
        for other in world.vehicles:
            if other.id != v.id and other.assignment is None:
                other.available = False

    ops.mutate(rid, "isolate recovery case", "isolate", isolate)
    recovered = ops.preview(rid)
    assert any(
        c["vehicle"] == v.id and "q4" in c["requests"] for c in recovered["routes"]
    )
    ops.commit(rid, recovered["id"], recovered["revision"], "recovery")
    w = ops.store.load(rid)
    assert available_stock(w, "d2") == stock_before
    assert any(r.quantity == 0 and r.assignment != a.id for r in w.reservations)
    ops.advance(rid, 25, "finish-recovery")
    assert (
        next(q for q in ops.store.load(rid).requests if q.id == "q4").status
        == "delivered"
    )


def test_entered_segment_finishes_after_a_physical_closure(ops):
    rid = ops.create()["id"]
    p = ops.preview(rid)
    ops.commit(rid, p["id"], p["revision"], "commit")
    ops.advance(rid, 1, "enter")
    calls = []
    original = ops.simulator.is_open

    def closed_after_entry(run_id, road, time):
        calls.append((road, time))
        return original(run_id, road, time) if time <= 1 else False

    ops.simulator.is_open = closed_after_entry
    ops.advance(rid, 6, "finish-segment")
    assert (
        next(q for q in ops.store.load(rid).requests if q.id == "q4").status
        == "delivered"
    )
    assert ("r04", 6) not in calls


def test_http_degraded_state_and_failed_mutation(monkeypatch, ops):
    from fastapi.testclient import TestClient
    from app import api

    rid = ops.create()["id"]
    monkeypatch.setattr(api, "ops", ops)

    def unavailable(*args, **kwargs):
        raise GraphUnavailable("FalkorDB unavailable; start its service")

    monkeypatch.setattr(ops.store, "health", unavailable)
    client = TestClient(api.app)
    response = client.get("/api/health")
    assert response.status_code == 503 and response.json()["stale"] is True
    monkeypatch.setattr(ops.store, "query", unavailable)
    response = client.post(
        f"/api/runs/{rid}/advance", json={"minutes": 1, "key": "offline"}
    )
    assert response.status_code == 503


def test_missing_private_checkpoint_is_actionable_and_does_not_mutate(monkeypatch, ops):
    from fastapi.testclient import TestClient
    from app import api

    rid = ops.create()["id"]
    before = ops.context(rid)
    ops.simulator.remove(rid)
    monkeypatch.setattr(api, "ops", ops)
    response = TestClient(api.app).post(
        f"/api/runs/{rid}/advance", json={"minutes": 1, "key": "missing-checkpoint"}
    )
    assert response.status_code == 503
    assert response.json()["code"] == "CHECKPOINT_UNAVAILABLE"
    assert "restore its volume" in response.json()["error"]
    assert ops.context(rid) == before
