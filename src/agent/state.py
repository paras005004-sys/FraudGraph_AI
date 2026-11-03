"""
InvestigationState Definition — FraudGraph AI Phase 6
======================================================
Defines the state representation for the LangGraph agent orchestrator.
Preserves:
- Case & trigger alert details
- Graph & vector evidence
- Derived risk & exposure metrics
- Simulated evidence requests
- Deterministic policy decisions
- SAR regulatory report data
- Execution telemetry & stopping criteria
"""

from typing import TypedDict, List, Dict, Any, Optional
from dataclasses import dataclass, field


class EvidenceRequestDict(TypedDict, total=False):
    type: str                # "customer_validation" | "step_up_auth" | "analyst_info"
    asked_after_step: int
    assumed_response: str


class EvidenceItemDict(TypedDict, total=False):
    claim: str
    source: str              # "graph" | "document" | "customer" | "external"
    ref: str
    entity_ids: List[str]


class ActionItemDict(TypedDict, total=False):
    action: str
    route: str               # "auto" | "L1" | "L2"
    reason: str


class NextBestActionsDict(TypedDict, total=False):
    initial: List[ActionItemDict]
    final: List[ActionItemDict]
    what_changed: str


class SARDict(TypedDict, total=False):
    file: bool
    reason: str
    narrative: str
    subjects: List[str]
    total_amount_usd: float
    activity_dates: List[str]


class TelemetryEvent(TypedDict, total=False):
    node: str
    step: int
    timestamp: str
    action: str
    details: Dict[str, Any]


class CaseDict(TypedDict, total=False):
    status: str              # "open" | "closed_fraud" | "closed_legitimate" | "escalated"
    verdict: str             # "fraud" | "legitimate" | "uncertain"
    fraud_probability: float
    pattern: str             # "card_testing" | "card_not_present_fraud" | ...
    pattern_description: str
    affected_txn_ids: List[str]
    first_suspicious_txn_id: str
    connected_card_ids: List[str]
    connected_device_profiles: List[str]
    exposure_usd: float
    evidence: List[EvidenceItemDict]
    similar_prior_cases: List[str]
    summary: str
    written_to_graph: bool
    graph_case_id: str


class InvestigationState(TypedDict, total=False):
    # 1. Alert & Input Information
    case_id: str
    opened_at: str
    trigger_type: str        # "risk_score" | "customer_report" | "analyst_request"
    trigger_text: str
    flagged_txn_id: str
    card_id: str
    customer_id: str
    initial_risk_score: Optional[float]

    # 2. Graph Evidence (Phase 4 tools)
    transaction_details: Dict[str, Any]
    card_history: Dict[str, Any]
    connected_entities: Dict[str, Any]
    shared_devices: Dict[str, Any]
    neighborhood: Dict[str, Any]
    connected_transactions: Dict[str, Any]
    historical_cases: Dict[str, Any]
    card_testing_result: Dict[str, Any]
    out_of_region_result: Dict[str, Any]

    # 3. Vector Evidence (Phase 5 RAG)
    similar_prior_cases: List[str]
    retrieved_patterns: List[str]
    retrieved_regulatory_refs: List[str]
    retrieved_policy_rules: List[str]

    # 4. Synthesized Evidence Items
    evidence: List[EvidenceItemDict]

    # 5. Risk & Metric Assessment
    fraud_probability: float
    exposure_usd: float
    confidence: float
    signal_count: int
    verdict: str             # "fraud" | "legitimate" | "uncertain"
    pattern: str
    pattern_description: str
    affected_txn_ids: List[str]
    first_suspicious_txn_id: str
    connected_card_ids: List[str]
    connected_device_profiles: List[str]

    # 6. Verification / Evidence Requests (Section 5)
    evidence_requests: List[EvidenceRequestDict]
    customer_verified: Optional[bool]
    customer_response_text: str
    hours_since_request: Optional[float]

    # 7. Policy Decisions (Phase 5 Engine)
    initial_actions: List[ActionItemDict]
    final_actions: List[ActionItemDict]
    what_changed: str
    next_best_actions: NextBestActionsDict

    # 8. SAR Data (Section 3a / Answer format)
    sar: SARDict

    # 9. Case Output
    status: str              # "open" | "closed_fraud" | "closed_legitimate" | "escalated"
    summary: str
    written_to_graph: bool
    graph_case_id: str
    graph_write_mode: str    # "live_tigergraph" | "offline_simulated"

    # 10. Execution Telemetry & Stopping Control
    step_count: int
    max_steps: int
    should_stop: bool
    stop_reason: str
    tool_calls: int
    tokens: int
    latency_s: float
    telemetry: List[TelemetryEvent]
    errors: List[str]
