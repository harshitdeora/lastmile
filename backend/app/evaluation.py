"""Isolated evaluation; truth never enters a controller response."""

import csv
import hashlib
import json
from pathlib import Path
from random import Random
from time import perf_counter
from .service import Operations

RESULT_DIR = Path(__file__).resolve().parents[2] / "benchmarks"
if not RESULT_DIR.exists():
    RESULT_DIR = Path(__file__).resolve().parents[3] / "benchmarks"


def benchmark(ops=None, count=10):
    ops = ops or Operations()
    rows = []
    for seed in range(count):
        scenario = ("critical_crossing", "capacity_disruption", "no_useful_inspection")[
            seed % 3
        ]
        fingerprints = []
        for policy in ("none", "random", "value"):
            context = ops.create(scenario, seed)
            run_id = context["id"]
            initial = {k: v for k, v in context.items() if k != "id"}
            digest = hashlib.sha256(
                json.dumps(initial, sort_keys=True).encode()
            ).hexdigest()
            fingerprints.append(digest)
            rng = Random(10000 + seed)  # policy RNG is independent of world RNG
            start = perf_counter()
            while True:
                w = ops.store.load(run_id)
                if w.status != "active" or w.cycles >= 30:
                    break
                ops.deterministic_cycle(run_id, policy, rng)
            w = ops.store.load(run_id)
            solver_seconds = 0
            statuses = set()
            for decision in w.decisions:
                for call in decision.calls:
                    result = call.get("result", {})
                    solver_seconds += result.get(
                        "solver_seconds",
                        result.get("plan", {}).get("solver_seconds", 0),
                    )
                    if result.get("status"):
                        statuses.add(result["status"])
                    if result.get("plan", {}).get("status"):
                        statuses.add(result["plan"]["status"])
                    for candidate in result.get("candidates", []):
                        statuses.update(candidate.get("branch_solver_status", []))
            rows.append(
                dict(
                    seed=seed,
                    scenario=scenario,
                    policy=policy,
                    run_id=run_id,
                    initial_fingerprint=digest,
                    **w.calculate_metrics(),
                    simulation_time=w.time,
                    solver_seconds=round(solver_seconds, 4),
                    solver_status=";".join(sorted(statuses)),
                    controller_mode="Deterministic demo",
                    llm_calls=0,
                    llm_latency=0,
                    wall_seconds=round(perf_counter() - start, 3)
                )
            )
        if len(set(fingerprints)) != 1:
            raise AssertionError(
                "Policies did not receive identical starting observations"
            )
    aggregate = []
    for policy in ("none", "random", "value"):
        selected = [r for r in rows if r["policy"] == policy]
        aggregate.append(
            dict(
                policy=policy,
                runs=len(selected),
                mean_utility=round(
                    sum(r["utility"] for r in selected) / len(selected), 3
                ),
                mean_on_time_kits=round(
                    sum(r["on_time_kits"] for r in selected) / len(selected), 3
                ),
                mean_inspections=round(
                    sum(r["inspections"] for r in selected) / len(selected), 3
                ),
            )
        )
    comparisons = []
    for seed in range(count):
        outcomes = {r["policy"]: r["utility"] for r in rows if r["seed"] == seed}
        diff = outcomes["value"] - outcomes["none"]
        comparisons.append(
            dict(
                seed=seed,
                **outcomes,
                delta=diff,
                result="win" if diff > 0 else "regression" if diff < 0 else "tie"
            )
        )
    output = dict(
        synthetic=True,
        model="bounded two-stop CP-SAT",
        suite_runs=count * 3,
        rows=rows,
        aggregate=aggregate,
        comparisons=comparisons,
        note="Identical initial observations and immutable time-based physical schedules per seed. No live LLM benchmark.",
    )
    RESULT_DIR.mkdir(exist_ok=True)
    (RESULT_DIR / "results.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )
    with (RESULT_DIR / "results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return output


if __name__ == "__main__":
    print(json.dumps(benchmark()["aggregate"], indent=2))
