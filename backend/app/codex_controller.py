"""Authenticated localhost bridge to the official, already signed-in Codex runtime."""

import os
from time import monotonic
import httpx
from .agents import tool_definitions, evidence_from_calls
from .graph import Conflict

_health_cache = {"at": 0, "ready": False}


def codex_ready():
    url = os.getenv("CODEX_BRIDGE_URL", "")
    if not url or not os.getenv("CODEX_BRIDGE_TOKEN"):
        return False
    if monotonic() - _health_cache["at"] < 5:
        return _health_cache["ready"]
    try:
        response = httpx.get(
            url + "/health",
            timeout=2,
            trust_env=False,
            headers={"Authorization": "Bearer " + os.environ["CODEX_BRIDGE_TOKEN"]},
        )
        data = response.json()
        ready = (
            response.status_code == 200
            and data.get("service") == "lastmile-codex-bridge"
            and data.get("ready") is True
            and data.get("authenticated") is True
        )
    except (httpx.HTTPError, ValueError):
        ready = False
    _health_cache.update(at=monotonic(), ready=ready)
    return ready


def codex_cycle(ops, run_id, client=None):
    before = ops.store.load(run_id)
    if before.status != "active" or before.cycles >= 30:
        return {"stopped": True, "reason": "Run complete or 30-cycle limit reached"}
    url = os.getenv("CODEX_BRIDGE_URL", "")
    token = os.getenv("CODEX_BRIDGE_TOKEN", "")
    if not url or not token:
        raise Conflict(
            "Codex connection is not configured. Run scripts/start-codex.ps1 on this computer."
        )
    error = None
    try:
        caller = client or httpx
        response = caller.post(
            url + "/cycle",
            json={"run_id": run_id, "tools": tool_definitions()},
            headers={"Authorization": "Bearer " + token},
            timeout=115,
            **({"trust_env": False} if client is None else {})
        )
        response.raise_for_status()
        result = response.json()
        if not result.get("completed") or not result.get("calls"):
            error = (
                result.get("error")
                or "Codex did not complete an application tool cycle."
            )
    except (httpx.HTTPError, ValueError):
        result = {
            "calls": [],
            "evidence": [],
            "model": None,
            "summary": "Codex connection failed. Check the local bridge and Codex sign-in.",
        }
        error = (
            "Codex bridge unavailable; committed actions, if any, remain in the graph."
        )
    summary = (result.get("summary") or "Codex controller cycle.")[:1600]
    if error:
        summary = error
    calls = result.get("calls", [])[:12]
    evidence = sorted(evidence_from_calls(calls))[:40]
    calls.append(
        {
            "provider": "codex_app_server",
            "model": result.get("model"),
            "authentication": "Codex-managed ChatGPT sign-in",
            "completed": not bool(error),
            "tool_calls": len(calls),
            "latency_seconds": result.get("latency_seconds"),
            "error": error,
        }
    )
    ops.record_controller(run_id, "Codex · ChatGPT plan", summary, evidence, calls)
    return {
        "mode": "Codex · ChatGPT plan",
        "model": result.get("model"),
        "summary": summary,
        "calls": calls,
        "completed": not bool(error),
        "error": error,
    }
