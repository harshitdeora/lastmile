"""Opt-in live verification; consumes the local signed-in Codex plan allowance."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument(
    "--run-id",
    help="Continue an existing explicit smoke run, otherwise create an isolated world",
)
args = parser.parse_args()
base = "http://127.0.0.1:8000/api"


def call(path, body=None):
    request = Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read())


health = call("/health")
assert health["codex_configured"], "Start scripts/start-codex.ps1 first"
run = (
    call("/runs/" + args.run_id)
    if args.run_id
    else call("/runs", {"scenario": "critical_crossing", "seed": 9})
)
rid = run["id"]
for cycle in range(6):
    if run["status"] != "active":
        break
    result = call("/runs/" + rid + "/cycle", {"mode": "codex"})
    assert result.get("completed") is True, result.get("error")
    run = call("/runs/" + rid)
    print(
        f"Live Codex: time {run['time']}, {run['metrics']['on_time_requests']} on-time deliveries, {run['metrics']['delivered_kits']} kits",
        flush=True,
    )
assert (
    run["metrics"]["on_time_requests"] == 6 and run["metrics"]["delivered_kits"] == 42
)
decisions = [d for d in run["decisions"] if d["mode"] == "Codex · ChatGPT plan"]
report = {
    "verified_at_utc": datetime.now(timezone.utc).isoformat(),
    "provider": "Official Codex app-server",
    "authentication": "Existing local Codex ChatGPT sign-in; no credentials copied or exported",
    "run_id": rid,
    "scenario": run["scenario"],
    "metrics": run["metrics"],
    "simulation_time": run["time"],
    "decisions": [
        {
            "id": d["id"],
            "time": d["time"],
            "summary": d["summary"],
            "evidence": d["evidence"],
            "tools": [c["tool"] for c in d["calls"] if "tool" in c],
            "provider": next(
                c for c in d["calls"] if c.get("provider") == "codex_app_server"
            ),
        }
        for d in decisions
    ],
}
destination = Path(__file__).resolve().parents[1] / "docs" / "live-codex-smoke.json"
destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(
    "PASS live Codex tool orchestration: 6 requests / 42 kits on time. Evidence saved to docs/live-codex-smoke.json"
)
