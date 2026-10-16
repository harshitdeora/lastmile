"""Schemas for controller-visible tool results, separate from provider input schemas."""

from .domain import Model, World, Report, Plan, Inspection, Decision


class ContextOutput(World):
    metrics: dict[str, int]
    stock_available: dict[str, int]
    synthetic: bool


class CandidateOutput(Model):
    road: str
    name: str
    prior: float
    prior_source: str
    minutes: int
    open_utility: int
    closed_utility: int
    expected_utility: float
    gain: float
    affected_requests: list[str]
    evidence_ids: list[str]
    branch_solver_status: list[str]


class RankOutput(Model):
    base_utility: int
    candidates: list[CandidateOutput]
    recommendation: str
    revision: int
    solver_seconds: float
    limits: str = "No eligible inspection candidates"


class ImpactOutput(Model):
    revision: int
    road: str
    graph_rows: list[list]
    hypothetical_requests: list[str]
    reports: list[Report]


class InspectOutput(Model):
    inspection: Inspection
    revision: int


class CommitOutput(Model):
    plan: Plan
    revision: int


class AdvanceOutput(Model):
    time: int
    metrics: dict[str, int]
    revision: int


class EvidenceOutput(Model):
    revision: int
    decision: Decision | None
    graph: list[list]


OUTPUTS = {
    "get_operational_context": ContextOutput,
    "trace_disruption_impact": ImpactOutput,
    "rank_inspections": RankOutput,
    "inspect_road": InspectOutput,
    "propose_delivery_plan": Plan,
    "commit_delivery_plan": CommitOutput,
    "advance_simulation": AdvanceOutput,
    "get_decision_evidence": EvidenceOutput,
}
