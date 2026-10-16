"""Private truth boundary. This module is imported by execution/evaluation only.

Checkpoint is immutable per run: future changes are a pure function of simulated time.
No random draw occurs during controller execution. Checkpoints are never served.
"""

import json
import os
from pathlib import Path
from random import Random


class Simulator:
    def __init__(self, directory: str | None = None):
        self.directory = Path(directory or os.getenv("PRIVATE_STATE_DIR", ".private"))
        self.directory.mkdir(parents=True, exist_ok=True)

    def create(self, run_id: str, scenario: str, seed: int):
        rng = Random(seed)
        truth = {f"r{i:02}": True for i in range(1, 26)}
        truth["r08"] = rng.random() < 0.65
        truth["r22"] = rng.random() < 0.35
        schedule = (
            [{"time": 18, "kind": "vehicle", "id": "v3"}]
            if scenario == "capacity_disruption"
            else []
        )
        # Adverse worlds have a time-based, pre-generated physical closure.
        if seed % 4 == 3:
            schedule.append({"time": 26, "kind": "road", "id": "r10", "open": False})
        self._file(run_id).write_text(
            json.dumps({"initial": truth, "schedule": schedule}), encoding="utf-8"
        )

    def _file(self, run_id):
        if not run_id.isalnum():
            raise ValueError("Invalid run ID")
        return self.directory / f"{run_id}.json"

    def _load(self, run_id):
        try:
            return json.loads(self._file(run_id).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Private simulator checkpoint missing; restore its volume or explicitly reset this run"
            ) from exc

    def is_open(self, run_id: str, road: str, time: int):
        data = self._load(run_id)
        result = data["initial"][road]
        for event in data["schedule"]:
            if (
                event["kind"] == "road"
                and event["id"] == road
                and event["time"] <= time
            ):
                result = event["open"]
        return result

    def delivered_events(self, run_id: str, time: int):
        # Vehicle announcements are observable only once their scheduled time is reached.
        return [
            e
            for e in self._load(run_id)["schedule"]
            if e["kind"] == "vehicle" and e["time"] <= time
        ]

    def remove(self, run_id):
        self._file(run_id).unlink(missing_ok=True)
