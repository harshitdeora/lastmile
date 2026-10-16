from types import SimpleNamespace
import httpx
from fastapi.testclient import TestClient
from app import api
from app.codex_controller import codex_cycle, codex_ready
from test_lastmile import ops


def test_codex_callback_requires_auth_and_is_idempotent(ops, monkeypatch):
    rid = ops.create()["id"]
    monkeypatch.setattr(api, "ops", ops)
    monkeypatch.setenv("CODEX_BRIDGE_TOKEN", "a" * 40)
    client = TestClient(api.app)
    body = {
        "name": "advance_simulation",
        "arguments": {"minutes": 1},
        "call_id": "one-call",
    }
    path = f"/api/internal/codex/{rid}/tool"
    assert client.post(path, json=body).status_code == 403
    assert ops.context(rid)["time"] == 0
    headers = {"Authorization": "Bearer " + "a" * 40}
    first = client.post(path, json=body, headers=headers)
    assert first.status_code == 200
    assert client.post(path, json=body, headers=headers).json() == first.json()
    assert ops.context(rid)["time"] == 1
    body["name"] = "raw_cypher"
    assert client.post(path, json=body, headers=headers).status_code == 400


def test_codex_bridge_failure_never_claims_live_success(ops, monkeypatch):
    monkeypatch.setenv("CODEX_BRIDGE_URL", "http://bridge")
    monkeypatch.setenv("CODEX_BRIDGE_TOKEN", "a" * 40)
    rid = ops.create()["id"]

    class Client:
        def post(self, *args, **kwargs):
            raise httpx.ConnectError("not available")

    result = codex_cycle(ops, rid, Client())
    assert result["completed"] is False and result["error"]
    context = ops.context(rid)
    assert context["time"] == 0 and context["budget"] == 2
    metadata = context["decisions"][-1]["calls"][-1]
    assert metadata["completed"] is False and metadata["tool_calls"] == 0


def test_codex_health_requires_authenticated_bridge(monkeypatch):
    from app import codex_controller

    monkeypatch.setenv("CODEX_BRIDGE_URL", "http://bridge")
    monkeypatch.setenv("CODEX_BRIDGE_TOKEN", "a" * 40)
    monkeypatch.setattr(codex_controller, "_health_cache", {"at": 0, "ready": False})
    response = SimpleNamespace(
        status_code=200,
        json=lambda: {
            "service": "lastmile-codex-bridge",
            "ready": True,
            "authenticated": False,
        },
    )
    monkeypatch.setattr(codex_controller.httpx, "get", lambda *args, **kwargs: response)
    assert codex_ready() is False


def test_codex_rejects_unregistered_tools_before_starting_a_model():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "codex_bridge.py"
    spec = importlib.util.spec_from_file_location("lastmile_bridge", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    import pytest

    with pytest.raises(ValueError, match="fixed LastMile tool"):
        module.execute_cycle(
            {"run_id": "a" * 32, "tools": []}, "a" * 40, "http://localhost:8000"
        )


def test_live_decision_links_returned_reports_and_continued_plan(ops):
    from app.agents import dispatch, evidence_from_calls

    rid = ops.create()["id"]
    preview = ops.preview(rid)
    ops.commit(rid, preview["id"], preview["revision"], "commit")
    calls = [
        {
            "tool": "get_operational_context",
            "result": dispatch(ops, rid, "get_operational_context", {}),
        },
        {
            "tool": "rank_inspections",
            "result": {"candidates": [{"evidence_ids": ["r08", "report-bridge-1"]}]},
        },
    ]
    evidence = sorted(evidence_from_calls(calls))
    ops.record_controller(
        rid,
        "Codex · ChatGPT plan",
        "Continue the existing plan based on returned evidence.",
        evidence,
        calls,
    )
    w = ops.store.load(rid)
    d = w.decisions[-1]
    result = ops.evidence(rid, d.id)
    assert d.plan == preview["id"]
    assert "report-bridge-1" in result["graph"][0][1]
    assert preview["id"] in result["graph"][0][2]
