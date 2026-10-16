"""Verify the owned Compose services' restart/outage semantics (run from repo root)."""

import json
import subprocess
import time
from uuid import uuid4
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000/api", timeout=35)


def post(path, body):
    response = client.post(path, json=body)
    response.raise_for_status()
    return response.json()


def wait_ready():
    for _ in range(40):
        try:
            response = client.get("/health")
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError("Compose backend did not become healthy")


def state(rid):
    response = client.get("/runs/" + rid)
    response.raise_for_status()
    return response.json()


wait_ready()
run = post("/runs", {"scenario": "critical_crossing", "seed": 9})
rid = run["id"]
base = "/runs/" + rid
post(base + "/inspect", {"road": "r08", "key": uuid4().hex})
plan = client.get(base + "/plan").json()
post(
    base + "/commit",
    {"plan_id": plan["id"], "expected_revision": plan["revision"], "key": uuid4().hex},
)
post(base + "/advance", {"minutes": 1, "key": uuid4().hex})
before = state(rid)
subprocess.run(["docker", "compose", "restart", "backend"], check=True)
wait_ready()
assert state(rid) == before, "Backend restart altered operational state"
print(
    "PASS backend restart: budget, evidence, events, active movement, stock and revision identical"
)
subprocess.run(["docker", "compose", "stop", "falkordb"], check=True)
response = client.get("/health")
assert response.status_code == 503 and response.json()["stale"] is True
response = client.post(base + "/advance", json={"minutes": 1, "key": uuid4().hex})
assert response.status_code == 503, "Offline mutation returned success"
print("PASS real database outage: health and mutation return explicit HTTP 503")
subprocess.run(["docker", "compose", "up", "-d", "--wait", "falkordb"], check=True)
wait_ready()
assert state(rid) == before, "Database restart or failed mutation changed state"
print("PASS database restart: graph records and event sequence identical")
post(base + "/inspect", {"road": "r22", "key": uuid4().hex})
after = state(rid)
assert after["budget"] == 0 and after["time"] == 24
print("PASS private checkpoint resumed: real inspection completed after both restarts")
print(
    json.dumps(
        {
            "run": rid,
            "revision": after["revision"],
            "time": after["time"],
            "budget": after["budget"],
        }
    )
)
