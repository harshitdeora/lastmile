"""FalkorDB is the only authoritative observed-state store.

Each Entity.data is the typed record; indexed/traversal fields are projections
updated in the SAME atomic GRAPH.QUERY. There is no write-behind cache.
"""

from collections import deque
import json
import os
from pathlib import Path
import re
from time import perf_counter
from falkordb import FalkorDB
from .domain import World

ROOT = Path(__file__).resolve().parents[2]
QUERIES = ROOT / "queries"
if not QUERIES.exists():
    QUERIES = ROOT.parent / "queries"

LABELS = {
    "locations": "Location",
    "roads": "Road",
    "requests": "DeliveryRequest",
    "depots": "Stock",
    "vehicles": "Vehicle",
    "reports": "Report",
    "assignments": "Assignment",
    "reservations": "Reservation",
    "inspections": "Inspection",
    "plans": "Plan",
    "decisions": "Decision",
    "events": "Event",
}


class GraphUnavailable(RuntimeError):
    pass


class Conflict(ValueError):
    pass


class GraphStore:
    def __init__(self):
        self._db = None
        self.audit = deque(maxlen=150)

    @property
    def db(self):
        if self._db is None:
            try:
                self._db = FalkorDB(
                    host=os.getenv("FALKOR_HOST", "localhost"),
                    port=int(os.getenv("FALKOR_PORT", "6380")),
                    password=os.getenv("FALKOR_PASSWORD") or None,
                    socket_timeout=20,
                    socket_connect_timeout=3,
                )
            except Exception as exc:
                raise GraphUnavailable(
                    "Cannot connect to FalkorDB. Start docker compose up -d falkordb and check FALKOR_HOST/PORT."
                ) from exc
        return self._db

    def graph(self, run_id):
        if not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise ValueError("Run ID must be a 32-character hexadecimal ID")
        return self.db.select_graph("lastmile_" + run_id)

    def query(self, run_id, name, params=None):
        query = (QUERIES / f"{name}.cypher").read_text(encoding="utf-8")
        start = perf_counter()
        try:
            result = self.graph(run_id).query(query, params or {}).result_set
        except Exception as exc:
            raise GraphUnavailable(
                f"FalkorDB query '{name}' failed. Start docker compose up -d falkordb and check FALKOR_HOST/PORT."
            ) from exc
        returned = re.findall(
            r"\b(?:r\d{2}|q\d|v\d|report-[\w-]+|decision-[\w-]+|plan-[\w-]+|assignment-[\w-]+)\b",
            str(result),
        )
        self.audit.append(
            dict(
                run=run_id,
                query=name,
                parameters=params or {},
                returned_ids=sorted(set(returned))[:80],
                rows=len(result),
                milliseconds=round((perf_counter() - start) * 1000, 2),
            )
        )
        return result

    def health(self):
        try:
            self.db.connection.ping()
            result = (
                self.db.select_graph("lastmile_health").query("RETURN 1").result_set
            )
            if result != [[1]]:
                raise RuntimeError("GRAPH.QUERY unavailable")
            return True
        except Exception as exc:
            raise GraphUnavailable(
                "FalkorDB unavailable or GRAPH.QUERY missing. Run docker compose up -d falkordb."
            ) from exc

    def list_runs(self):
        self.health()
        result = []
        for name in self.db.connection.execute_command("GRAPH.LIST"):
            name = name.decode() if isinstance(name, bytes) else name
            if re.fullmatch(r"lastmile_[a-f0-9]{32}", name):
                rows = self.query(name[9:], "resume")
                if rows:
                    metadata = json.loads(rows[0][0])
                    result.append(
                        {
                            k: metadata[k]
                            for k in ("id", "scenario", "time", "revision", "status")
                        }
                    )
        return result

    def load(self, run_id):
        meta = self.query(run_id, "resume")
        if not meta:
            raise ValueError("Run not found")
        data = json.loads(meta[0][0])
        for key in LABELS:
            data[key] = []
        for kind, payload in self.query(run_id, "load"):
            if kind in data:
                data[kind].append(json.loads(payload))
        for key in LABELS:
            data[key].sort(key=lambda x: x.get("seq", x["id"]))
        return World.model_validate(data)

    def save(self, w: World, expected: int, initial=False):
        graph = self.graph(w.id)
        if initial:
            graph.query(
                "MERGE (r:Run {id:$id}) ON CREATE SET r.revision=-1", {"id": w.id}
            )
            for label in ("Entity", "Location", "Road", "DeliveryRequest", "Decision"):
                graph.query(f"CREATE INDEX FOR (n:{label}) ON (n.id)")
        payload = w.model_dump()
        metadata = {k: v for k, v in payload.items() if k not in LABELS}
        params = {
            "id": w.id,
            "expected": expected,
            "revision": w.revision,
            "metadata": json.dumps(metadata),
            "snapshot": w.model_dump_json(),
            "time": w.time,
            "snapshot_id": f"snapshot-{w.revision}",
        }
        for key, label in LABELS.items():
            rows = []
            for obj in payload[key]:
                entity_id = "stock-" + obj["id"] if key == "depots" else obj["id"]
                props = {"id": entity_id, "kind": key, "data": json.dumps(obj)}
                if key == "locations":
                    props.update(type=obj["kind"])
                if key == "requests":
                    props.update(status=obj["status"])
                if key == "roads":
                    props.update(status=obj["status"], valid_until=obj["valid_until"])
                if key == "assignments":
                    props.update(state=obj["state"])
                rows.append({"id": entity_id, "props": props})
            params[key] = rows
        params["edges"] = [
            dict(
                a=r.a,
                b=r.b,
                id=r.id,
                status=r.status,
                minutes=r.minutes,
                valid_until=r.valid_until,
            )
            for r in w.roads
        ]
        params["reverse"] = [
            dict(
                a=r.b,
                b=r.a,
                id=r.id,
                status=r.status,
                minutes=r.minutes,
                valid_until=r.valid_until,
            )
            for r in w.roads
            if r.bidirectional
        ]
        relations = []
        for r in w.reports:
            relations.append((r.id, "DESCRIBES", r.road))
        for i in w.inspections:
            relations.append((i.id, "DESCRIBES", i.road))
        for q in w.requests:
            relations.append((q.id, "DESTINATION", q.destination))
        for a in w.assignments:
            relations.extend(
                (a.id, "USES", leg.road) for leg in a.route.legs if leg.road
            )
            relations.extend((a.id, "FULFILLS", q) for q in a.route.requests)
            relations.extend(
                [(a.id, "USES_VEHICLE", a.route.vehicle), (a.id, "PART_OF", a.plan)]
            )
        for r in w.reservations:
            relations.extend(
                [(r.id, "HOLDS", "stock-" + r.depot), (r.id, "FOR", r.assignment)]
            )
        for d in w.decisions:
            existing = {obj["id"] for key in LABELS for obj in payload[key]}
            relations.extend((d.id, "BASED_ON", e) for e in d.evidence if e in existing)
            if d.plan:
                relations.append((d.id, "AFFECTS", d.plan))
        for rel in (
            "DESCRIBES",
            "DESTINATION",
            "USES",
            "FULFILLS",
            "USES_VEHICLE",
            "PART_OF",
            "HOLDS",
            "FOR",
            "BASED_ON",
            "AFFECTS",
        ):
            params["rel_" + rel] = [
                {"a": a, "b": b} for a, r, b in relations if r == rel
            ]
        # Executable mutation surface is a checked-in fixed template, never model-generated Cypher.
        statement = (QUERIES / "write.cypher").read_text(encoding="utf-8")
        try:
            result = graph.query(statement, params).result_set
        except Exception as exc:
            raise GraphUnavailable(
                "Atomic graph write failed; no successful mutation is reported. Check FalkorDB logs."
            ) from exc
        if not result:
            raise Conflict("Graph revision changed; refresh and preview again")

    def delete(self, run_id):
        self.graph(run_id).delete()

    def paths(self, run_id, source, target, now, override="", assume_open=False):
        if source == target:
            return [([source], [], 0)]
        return self.query(
            run_id,
            "paths",
            dict(
                source=source,
                target=target,
                now=now,
                override=override,
                assume_open=assume_open,
            ),
        )
