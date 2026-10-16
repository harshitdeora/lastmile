from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock, Thread
from uuid import uuid4
import json
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import Field
from .domain import Model
from .graph import GraphUnavailable, Conflict
from .service import Operations
from .scenarios import CATALOGUE
from .agents import llm_cycle
from .lease import acquire_process_lease
from .evaluation import benchmark, RESULT_DIR
from .agents import tool_definitions
from .tool_outputs import OUTPUTS

ops = Operations()
benchmark_state = {"status": "idle"}
benchmark_lock = Lock()
controller_lock = Lock()


@asynccontextmanager
async def lifespan(app):
    lease = acquire_process_lease()
    yield
    lease.close()


app = FastAPI(
    title="LastMile · fictional relief simulation", version="1.0.0", lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(GraphUnavailable)
def graph_error(request: Request, exc):
    return JSONResponse(
        status_code=503,
        content={"error": str(exc), "code": "GRAPH_UNAVAILABLE", "stale": True},
    )


@app.exception_handler(Conflict)
def conflict_error(request: Request, exc):
    return JSONResponse(
        status_code=409, content={"error": str(exc), "code": "CONFLICT"}
    )


@app.exception_handler(ValueError)
def input_error(request: Request, exc):
    return JSONResponse(
        status_code=400, content={"error": str(exc), "code": "INVALID_INPUT"}
    )


class CreateRun(Model):
    scenario: str = "critical_crossing"
    seed: int = Field(default=0, ge=0, le=1000000)
    inspection_budget: int = Field(default=2, ge=0, le=4)


class Key(Model):
    key: str = Field(min_length=1, max_length=128)


class Inspect(Key):
    road: str = Field(pattern=r"^r\d{2}$")


class Commit(Key):
    plan_id: str
    expected_revision: int = Field(ge=0)


class Advance(Key):
    minutes: int = Field(ge=1, le=180)


class Cycle(Model):
    mode: str = "deterministic"


@app.get("/api/health")
def health():
    ops.store.health()
    return dict(
        backend="healthy",
        database="FalkorDB · GRAPH.QUERY available",
        frontend="served separately",
        llm_configured=bool(os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL")),
        single_worker=True,
    )


@app.get("/api/scenarios")
def scenarios():
    return CATALOGUE


@app.get("/api/tools")
def tools():
    return {
        "inputs": tool_definitions(),
        "outputs": {name: cls.model_json_schema() for name, cls in OUTPUTS.items()},
    }


@app.get("/api/runs")
def runs():
    return ops.store.list_runs()


@app.post("/api/runs")
def create(body: CreateRun):
    return ops.create(body.scenario, body.seed, body.inspection_budget)


@app.get("/api/runs/{run_id}")
def context(run_id: str):
    return ops.context(run_id)


@app.get("/api/runs/{run_id}/rank")
def rank(run_id: str):
    return ops.rank(run_id)


@app.get("/api/runs/{run_id}/impact/{road}")
def impact(run_id: str, road: str):
    return ops.impact(run_id, road)


@app.get("/api/runs/{run_id}/plan")
def plan(run_id: str):
    return ops.preview(run_id)


@app.post("/api/runs/{run_id}/inspect")
def inspect(run_id: str, body: Inspect):
    return ops.inspect(run_id, body.road, body.key)


@app.post("/api/runs/{run_id}/commit")
def commit(run_id: str, body: Commit):
    return ops.commit(run_id, body.plan_id, body.expected_revision, body.key)


@app.post("/api/runs/{run_id}/advance")
def advance(run_id: str, body: Advance):
    return ops.advance(run_id, body.minutes, body.key)


@app.post("/api/runs/{run_id}/disrupt")
def disrupt(run_id: str, body: Key):
    return ops.disrupt(run_id, body.key)


@app.post("/api/runs/{run_id}/cycle")
def cycle(run_id: str, body: Cycle):
    if not controller_lock.acquire(blocking=False):
        raise Conflict("Another controller cycle is running")
    try:
        if body.mode == "deterministic":
            return ops.deterministic_cycle(run_id)
        if body.mode == "llm":
            return llm_cycle(ops, run_id)
        raise ValueError("Unknown controller mode")
    finally:
        controller_lock.release()


@app.get("/api/runs/{run_id}/events")
def events(run_id: str, after: int = 0):
    return [e for e in ops.context(run_id)["events"] if e["seq"] > after]


@app.get("/api/runs/{run_id}/replay")
def replay(run_id: str):
    return ops.replay(run_id)


@app.get("/api/runs/{run_id}/evidence/{decision}")
def evidence(run_id: str, decision: str):
    return ops.evidence(run_id, decision)


@app.get("/api/runs/{run_id}/queries")
def queries(run_id: str):
    ops.store.load(run_id)  # validate scope and DB health
    return [entry for entry in ops.store.audit if entry["run"] == run_id]


@app.get("/api/runs/{run_id}/bottlenecks")
def bottlenecks(run_id: str):
    return ops.store.query(run_id, "bottlenecks")


@app.post("/api/runs/{run_id}/reset")
def reset(run_id: str, body: CreateRun):
    with ops.lock:
        ops.store.load(run_id)
        ops.store.delete(run_id)
        ops.simulator.remove(run_id)
        return ops.create(body.scenario, body.seed, body.inspection_budget)


@app.get("/api/benchmarks")
def results():
    path = RESULT_DIR / "results.json"
    return {
        "job": benchmark_state,
        "results": (
            json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        ),
    }


@app.post("/api/benchmarks")
def start_benchmark():
    ops.store.health()
    if not benchmark_lock.acquire(blocking=False):
        raise Conflict("Benchmark already running")
    benchmark_state.update(status="running", job=uuid4().hex)

    def execute():
        try:
            benchmark(ops)
            benchmark_state.update(status="complete")
        except Exception as exc:
            benchmark_state.update(status="failed", error=type(exc).__name__)
        finally:
            benchmark_lock.release()

    Thread(target=execute, daemon=True).start()
    return benchmark_state
