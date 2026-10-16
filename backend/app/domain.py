"""Public observed state only. No simulator truth may be added here."""

from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Location(Model):
    id: str
    name: str
    kind: Literal["depot", "shelter", "junction"]
    x: int
    y: int


class Road(Model):
    id: str
    name: str
    a: str
    b: str
    minutes: int
    bidirectional: bool = True
    status: str = "VERIFIED_OPEN"
    observed_at: int = 0
    valid_until: int = 181
    prior: float = 0.65
    prior_source: str = "Synthetic scenario assumption, not a calibrated probability"
    inspection_minutes: int = 5
    inspection_validity: int = 90


class Report(Model):
    id: str
    road: str
    claim: str
    source: str
    authority: str = "unverified"
    observed_at: int
    received_at: int
    text: str


class Request(Model):
    id: str
    destination: str
    quantity: int
    deadline: int
    weight: int
    status: str = "outstanding"
    delivered_at: int | None = None


class Depot(Model):
    id: str
    stock: int


class Vehicle(Model):
    id: str
    name: str
    depot: str
    location: str
    capacity: int
    available: bool = True
    loaded: int = 0
    assignment: str | None = None


class Leg(Model):
    road: str
    start: str
    end: str
    minutes: int
    request: str | None = None


class Route(Model):
    vehicle: str
    depot: str
    requests: list[str]
    quantity: int
    legs: list[Leg]
    arrivals: dict[str, int]
    utility: int
    travel: int


class Plan(Model):
    id: str
    revision: int
    routes: list[Route]
    utility: int
    status: str
    solver_seconds: float
    unmet: list[dict]
    limits: str = (
        "At most 2 stops/vehicle; 12 hops/path; 6 alternatives/pair; 2s CP-SAT; no reloads"
    )


class Assignment(Model):
    id: str
    plan: str
    route: Route
    state: str = "reserved"
    index: int = 0
    entered_at: int | None = None
    exits_at: int | None = None


class Reservation(Model):
    id: str
    assignment: str
    depot: str
    quantity: int
    state: str = "reserved"


class Inspection(Model):
    id: str
    road: str
    result: str
    observed_at: int
    minutes: int


class Decision(Model):
    id: str
    time: int
    mode: str
    summary: str
    evidence: list[str]
    calls: list[dict] = Field(default_factory=list)
    plan: str | None = None


class Event(Model):
    id: str
    seq: int
    time: int
    kind: str
    summary: str
    ids: list[str] = Field(default_factory=list)


class World(Model):
    id: str
    scenario: str
    time: int = 0
    horizon: int = 180
    budget: int = 2
    revision: int = 0
    cycles: int = 0
    failed_traversals: int = 0
    replans: int = 0
    status: str = "active"
    locations: list[Location]
    roads: list[Road]
    requests: list[Request]
    depots: list[Depot]
    vehicles: list[Vehicle]
    reports: list[Report]
    assignments: list[Assignment] = Field(default_factory=list)
    reservations: list[Reservation] = Field(default_factory=list)
    inspections: list[Inspection] = Field(default_factory=list)
    plans: list[Plan] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    idempotency: dict[str, dict] = Field(default_factory=dict)

    def event(self, kind: str, summary: str, ids: list[str] | None = None):
        n = len(self.events) + 1
        self.events.append(
            Event(
                id=f"event-{n}",
                seq=n,
                time=self.time,
                kind=kind,
                summary=summary,
                ids=ids or [],
            )
        )

    def calculate_metrics(self):
        done = [r for r in self.requests if r.status == "delivered"]
        ontime = [r for r in done if r.delivered_at <= r.deadline]
        return dict(
            on_time_requests=len(ontime),
            delivered_kits=sum(r.quantity for r in done),
            on_time_kits=sum(r.quantity for r in ontime),
            utility=sum(r.quantity * r.weight for r in ontime),
            unmet_kits=sum(
                r.quantity for r in self.requests if r.status != "delivered"
            ),
            inspections=len(self.inspections),
            inspection_minutes=sum(i.minutes for i in self.inspections),
            failed_traversals=self.failed_traversals,
            replans=self.replans,
        )


def available_stock(w: World, depot: str) -> int:
    return next(d.stock for d in w.depots if d.id == depot) - sum(
        r.quantity for r in w.reservations if r.depot == depot and r.state != "released"
    )
