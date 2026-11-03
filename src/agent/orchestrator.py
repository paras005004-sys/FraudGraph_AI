"""
LangGraph Investigation Agent Orchestrator — FraudGraph AI Phase 6
===================================================================
Stateful agent orchestrator managing the full fraud investigation lifecycle:
trigger_handler -> evidence_gatherer -> pattern_matcher -> rag_retriever
-> risk_assessor -> sufficiency_evaluator -> policy_evaluator -> case_updater

Integrates:
- Phase 4: TigerGraph MCP investigation tools & LocalGraphClient fallback
- Phase 5A: Deterministic Policy Engine (R1-R10, initial/final NBA, approval routing)
- Phase 5B/C: Vector Store & Hybrid GraphRAG Retriever (cases, patterns, regulations, policy)
- Section 5: Deterministic customer/analyst evidence request simulation
- Section 6: Stopping criteria enforcement
- Section 7: Telemetry & answer-file schema generation
"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from langgraph.graph import StateGraph, END

from src.agent.state import (
    InvestigationState,
    EvidenceItemDict,
    EvidenceRequestDict,
    ActionItemDict,
    NextBestActionsDict,
    SARDict,
    TelemetryEvent,
    CaseDict
)
from src.tools.mcp_server import TigerGraphMCPServer
from src.rag.retriever import HybridGraphRAGRetriever
from src.policy.engine import (
    PolicyEngine,
    InvestigationContext,
    Action,
    ApprovalRoute
)

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class FraudInvestigationOrchestrator:
    """
    Stateful agent orchestrating end-to-end graph fraud investigations.
    """

    def __init__(
        self,
        mcp_server: Optional[TigerGraphMCPServer] = None,
        retriever: Optional[HybridGraphRAGRetriever] = None,
        policy_engine: Optional[PolicyEngine] = None
    ):
        self.mcp = mcp_server or TigerGraphMCPServer()
        self.retriever = retriever or HybridGraphRAGRetriever(mcp_server=self.mcp)
        self.policy_engine = policy_engine or PolicyEngine()
        self.graph = self._build_graph()

    # -------------------------------------------------------------------------
    # Graph Construction
    # -------------------------------------------------------------------------
    def _build_graph(self) -> Any:
        workflow = StateGraph(InvestigationState)

        # Add Nodes
        workflow.add_node("trigger_handler", self.node_trigger_handler)
        workflow.add_node("evidence_gatherer", self.node_evidence_gatherer)
        workflow.add_node("pattern_matcher", self.node_pattern_matcher)
        workflow.add_node("rag_retriever", self.node_rag_retriever)
        workflow.add_node("risk_assessor", self.node_risk_assessor)
        workflow.add_node("sufficiency_evaluator", self.node_sufficiency_evaluator)
        workflow.add_node("policy_evaluator", self.node_policy_evaluator)
        workflow.add_node("case_updater", self.node_case_updater)

        # Linear pipeline edges
        workflow.set_entry_point("trigger_handler")
        workflow.add_edge("trigger_handler", "evidence_gatherer")
        workflow.add_edge("evidence_gatherer", "pattern_matcher")
        workflow.add_edge("pattern_matcher", "rag_retriever")
        workflow.add_edge("rag_retriever", "risk_assessor")
        workflow.add_edge("risk_assessor", "sufficiency_evaluator")
        workflow.add_edge("sufficiency_evaluator", "policy_evaluator")
        workflow.add_edge("policy_evaluator", "case_updater")
        workflow.add_edge("case_updater", END)

        return workflow.compile()

    # -------------------------------------------------------------------------
    # Helper: Telemetry Logging
    # -------------------------------------------------------------------------
    def _log_telemetry(
        self,
        state: Dict[str, Any],
        node: str,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ) -> List[TelemetryEvent]:
        telemetry = list(state.get("telemetry", []))
        event: TelemetryEvent = {
            "node": node,
            "step": state.get("step_count", 0),
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {}
        }
        telemetry.append(event)
        return telemetry

    # -------------------------------------------------------------------------
    # Node 1: trigger_handler
    # -------------------------------------------------------------------------
    def node_trigger_handler(self, state: InvestigationState) -> Dict[str, Any]:
        """Validates incoming alert and initializes default state."""
        step = 1

        case_id = str(state.get("case_id", "UNKNOWN")).strip()
        txn_id = str(state.get("flagged_txn_id", "")).strip()
        card_id = str(state.get("card_id", "")).strip()
        cust_id = str(state.get("customer_id", "")).strip()
        trigger_type = str(state.get("trigger_type", "risk_score")).strip()

        errors = list(state.get("errors", []))
        if not case_id or case_id == "UNKNOWN":
            errors.append("Invalid or missing case_id")
        if not txn_id:
            errors.append("Missing flagged_txn_id")
        if not card_id:
            errors.append("Missing card_id")

        updates: Dict[str, Any] = {
            "case_id": case_id,
            "flagged_txn_id": txn_id,
            "card_id": card_id,
            "customer_id": cust_id,
            "trigger_type": trigger_type,
            "step_count": step,
            "max_steps": state.get("max_steps", 10),
            "tool_calls": 0,
            "tokens": 0,
            "should_stop": False,
            "stop_reason": "",
            "errors": errors,
            "evidence": list(state.get("evidence", [])),
            "evidence_requests": list(state.get("evidence_requests", []))
        }

        updates["telemetry"] = self._log_telemetry(
            state,
            node="trigger_handler",
            action="initialize_case",
            details={"case_id": case_id, "trigger_type": trigger_type, "errors_count": len(errors)}
        )
        return updates

    # -------------------------------------------------------------------------
    # Node 2: evidence_gatherer
    # -------------------------------------------------------------------------
    def node_evidence_gatherer(self, state: InvestigationState) -> Dict[str, Any]:
        """Calls Phase 4 graph tools to collect comprehensive entity context."""
        step = state.get("step_count", 1) + 1
        tool_calls = state.get("tool_calls", 0)
        evidence = list(state.get("evidence", []))
        errors = list(state.get("errors", []))

        txn_id = state.get("flagged_txn_id", "")
        card_id = state.get("card_id", "")

        # 1. Transaction details
        tx_res = self.mcp.get_transaction_details(txn_id)
        tool_calls += 1
        tx_data = tx_res.get("data", {}) if tx_res.get("status") == "success" else {}
        if not tx_data:
            errors.append(f"get_transaction_details: {tx_res.get('message', 'not found')}")
        else:
            t = tx_data.get("transaction", {}) or {}
            amt = float(t.get("TransactionAmt", 0.0) or 0.0)
            evidence.append({
                "claim": f"Flagged transaction {txn_id}: ${amt:.2f}, ts={t.get('ts')}, channel={t.get('channel')}, score={t.get('risk_score')}",
                "source": "graph",
                "ref": f"tool:get_transaction_details(txn_id={txn_id})",
                "entity_ids": [txn_id]
            })

        # 2. Card history
        hist_res = self.mcp.get_card_history(card_id, limit=50)
        tool_calls += 1
        card_hist = hist_res.get("data", {}) if hist_res.get("status") == "success" else {}
        if card_hist:
            evidence.append({
                "claim": f"Card {card_id} history contains {card_hist.get('total_transactions', 0)} total recorded transactions",
                "source": "graph",
                "ref": f"tool:get_card_history(card_id={card_id})",
                "entity_ids": [card_id]
            })

        # 3. Connected cards & customers
        conn_res = self.mcp.get_connected_cards_and_customers(card_id)
        tool_calls += 1
        conn_data = conn_res.get("data", {}) if conn_res.get("status") == "success" else {}

        # 4. Shared devices
        dev_res = self.mcp.find_shared_devices(card_id)
        tool_calls += 1
        dev_data = dev_res.get("data", {}) if dev_res.get("status") == "success" else {}
        if dev_data and dev_data.get("total_shared_cards_count", 0) > 0:
            evidence.append({
                "claim": f"Card {card_id} shares device profile(s) with {dev_data.get('total_shared_cards_count')} other card(s): {', '.join(dev_data.get('shared_cards', [])[:3])}",
                "source": "graph",
                "ref": f"tool:find_shared_devices(card_id={card_id})",
                "entity_ids": [card_id] + dev_data.get("shared_cards", [])[:3]
            })

        # 5. Transaction neighborhood
        nbr_res = self.mcp.get_transaction_neighborhood(txn_id, depth=2)
        tool_calls += 1
        nbr_data = nbr_res.get("data", {}) if nbr_res.get("status") == "success" else {}

        # 6. Connected transactions (NEXT chain)
        seq_res = self.mcp.get_connected_transactions(card_id)
        tool_calls += 1
        seq_data = seq_res.get("data", {}) if seq_res.get("status") == "success" else {}

        # 7. Historical closed cases
        cases_res = self.mcp.get_historical_closed_cases(card_id, limit=10)
        tool_calls += 1
        cases_data = cases_res.get("data", {}) if cases_res.get("status") == "success" else {}
        if cases_data and cases_data.get("case_count", 0) > 0:
            c_ids = [c.get("case_id") for c in cases_data.get("cases", [])[:3]]
            evidence.append({
                "claim": f"Card {card_id} is linked to {cases_data.get('case_count')} prior closed case(s): {', '.join(str(c) for c in c_ids)}",
                "source": "graph",
                "ref": f"tool:get_historical_closed_cases(card_id={card_id})",
                "entity_ids": [card_id] + [str(c) for c in c_ids]
            })

        updates = {
            "step_count": step,
            "tool_calls": tool_calls,
            "transaction_details": tx_data,
            "card_history": card_hist,
            "connected_entities": conn_data,
            "shared_devices": dev_data,
            "neighborhood": nbr_data,
            "connected_transactions": seq_data,
            "historical_cases": cases_data,
            "evidence": evidence,
            "errors": errors
        }
        updates["telemetry"] = self._log_telemetry(
            state,
            node="evidence_gatherer",
            action="gather_graph_evidence",
            details={"tool_calls_made": 7, "evidence_items": len(evidence)}
        )
        return updates

    # -------------------------------------------------------------------------
    # Node 3: pattern_matcher
    # -------------------------------------------------------------------------
    def node_pattern_matcher(self, state: InvestigationState) -> Dict[str, Any]:
        """Detects whether graph activity matches known or undocumented fraud patterns."""
        step = state.get("step_count", 2) + 1
        tool_calls = state.get("tool_calls", 0)
        evidence = list(state.get("evidence", []))
        card_id = state.get("card_id", "")
        flagged_txn = state.get("flagged_txn_id", "")

        # 1. Card testing pattern (Tool 8)
        ct_res = self.mcp.detect_card_testing_pattern(card_id)
        tool_calls += 1
        ct_data = ct_res.get("data", {}) if ct_res.get("status") == "success" else {}

        # 2. Out-of-region pattern (Tool 9)
        oor_res = self.mcp.detect_out_of_region_pattern(card_id)
        tool_calls += 1
        oor_data = oor_res.get("data", {}) if oor_res.get("status") == "success" else {}

        # Pattern identification logic
        pattern = "none"
        pattern_desc = ""
        affected_txns = [flagged_txn] if flagged_txn else []
        first_suspicious_txn = flagged_txn

        shared_dev = state.get("shared_devices", {})
        shared_cards = shared_dev.get("shared_cards", []) if shared_dev else []

        if ct_data.get("detected"):
            pattern = "card_testing"
            pattern_desc = "Three or more small online authorizations under $5 within an hour followed by a larger purchase."
            testing_txns = ct_data.get("testing_txns", [])
            affected_txns = sorted(list(set(testing_txns + ([flagged_txn] if flagged_txn else []))))
            first_suspicious_txn = testing_txns[0] if testing_txns else flagged_txn
            evidence.append({
                "claim": f"Card testing pattern identified: {len(testing_txns)} micro-authorizations preceding larger purchase.",
                "source": "graph",
                "ref": f"tool:detect_card_testing_pattern(card_id={card_id})",
                "entity_ids": [card_id] + testing_txns
            })
        elif oor_data.get("detected"):
            pattern = "out_of_region_use"
            pattern_desc = "Card-present transactions in a non-home billing region while home activity or retained card patterns exist."
            susp_txns = [t.get("tx_id") for t in oor_data.get("suspicious_txns", []) if t.get("tx_id")]
            affected_txns = sorted(list(set(susp_txns + ([flagged_txn] if flagged_txn else []))))
            first_suspicious_txn = susp_txns[0] if susp_txns else flagged_txn
            evidence.append({
                "claim": f"Out-of-region activity detected: transactions in region(s) {oor_data.get('foreign_regions')}.",
                "source": "graph",
                "ref": f"tool:detect_out_of_region_pattern(card_id={card_id})",
                "entity_ids": [card_id] + susp_txns
            })
        elif shared_cards and len(shared_cards) >= 2:
            pattern = "card_not_present_new_device"
            pattern_desc = "Online transactions sharing device profile across multiple distinct cards."
            evidence.append({
                "claim": f"Multiple cards ({len(shared_cards)}) share identical device profile across accounts.",
                "source": "graph",
                "ref": f"tool:find_shared_devices(card_id={card_id})",
                "entity_ids": [card_id] + shared_cards[:3]
            })

        connected_device_profiles = []
        if shared_dev and shared_dev.get("device_profiles"):
            connected_device_profiles = [p.get("device_profile_id", "") for p in shared_dev.get("device_profiles") if p.get("device_profile_id")]

        updates = {
            "step_count": step,
            "tool_calls": tool_calls,
            "card_testing_result": ct_data,
            "out_of_region_result": oor_data,
            "pattern": pattern,
            "pattern_description": pattern_desc,
            "affected_txn_ids": affected_txns,
            "first_suspicious_txn_id": first_suspicious_txn,
            "connected_card_ids": shared_cards,
            "connected_device_profiles": connected_device_profiles,
            "evidence": evidence
        }
        updates["telemetry"] = self._log_telemetry(
            state,
            node="pattern_matcher",
            action="match_fraud_patterns",
            details={"pattern": pattern, "affected_txns_count": len(affected_txns)}
        )
        return updates

    # -------------------------------------------------------------------------
    # Node 4: rag_retriever
    # -------------------------------------------------------------------------
    def node_rag_retriever(self, state: InvestigationState) -> Dict[str, Any]:
        """Queries Phase 5 Vector Store & GraphRAG for similar cases and policy guidance."""
        step = state.get("step_count", 3) + 1
        evidence = list(state.get("evidence", []))
        pattern = state.get("pattern", "none")
        card_id = state.get("card_id", "")

        query_text = f"fraud investigation {pattern} {card_id}"
        vector_res = self.retriever.retrieve_vector_only(query_text, n_cases=5, n_patterns=2, n_regulatory=2, n_rules=4)

        similar_cases = [r.doc.metadata.get("case_id") for r in vector_res.get("similar_cases", []) if r.doc.metadata.get("case_id")]
        retrieved_patterns = [r.doc.metadata.get("pattern_id") for r in vector_res.get("patterns", []) if r.doc.metadata.get("pattern_id")]
        retrieved_reg = [r.doc.metadata.get("ref_id") for r in vector_res.get("regulatory", []) if r.doc.metadata.get("ref_id")]
        retrieved_rules = [r.doc.metadata.get("rule_id") for r in vector_res.get("policy_rules", []) if r.doc.metadata.get("rule_id")]

        if similar_cases:
            evidence.append({
                "claim": f"GraphRAG identified {len(similar_cases)} relevant historical closed case(s): {', '.join(similar_cases[:3])}.",
                "source": "document",
                "ref": "tool:vector_search::closed_cases",
                "entity_ids": similar_cases[:3]
            })

        updates = {
            "step_count": step,
            "similar_prior_cases": similar_cases,
            "retrieved_patterns": retrieved_patterns,
            "retrieved_regulatory_refs": retrieved_reg,
            "retrieved_policy_rules": retrieved_rules,
            "evidence": evidence
        }
        updates["telemetry"] = self._log_telemetry(
            state,
            node="rag_retriever",
            action="retrieve_rag_context",
            details={"similar_cases_count": len(similar_cases), "retrieved_rules": retrieved_rules}
        )
        return updates

    # -------------------------------------------------------------------------
    # Node 5: risk_assessor
    # -------------------------------------------------------------------------
    def node_risk_assessor(self, state: InvestigationState) -> Dict[str, Any]:
        """Calculates exposure, fraud probability, signal count, and initial verdict."""
        step = state.get("step_count", 4) + 1
        pattern = state.get("pattern", "none")
        trigger_type = state.get("trigger_type", "risk_score")
        tx_details = state.get("transaction_details", {})
        tx = tx_details.get("transaction", {}) if tx_details else {}

        # 1. Exposure USD: Sum amounts of affected transactions
        affected_ids = set(state.get("affected_txn_ids", []))
        exposure = 0.0
        flagged_amt = float(tx.get("TransactionAmt", 0.0) or 0.0)
        exposure += flagged_amt

        # Add amounts from card history if part of affected
        card_hist = state.get("card_history", {})
        if card_hist and card_hist.get("transactions"):
            for t in card_hist.get("transactions", []):
                tid = str(t.get("TransactionID"))
                if tid in affected_ids and tid != str(state.get("flagged_txn_id")):
                    exposure += float(t.get("TransactionAmt", 0.0) or 0.0)

        # 2. Probability and Signals
        signal_count = 1
        initial_score = float(tx.get("risk_score", 0.5) or 0.5)
        if state.get("initial_risk_score") is not None:
            initial_score = float(state.get("initial_risk_score"))

        if trigger_type == "customer_report":
            fraud_prob = 0.88
            signal_count = 2
            confidence = 0.90
        elif pattern == "card_testing":
            fraud_prob = 0.89
            signal_count = 3
            confidence = 0.92
        elif pattern == "out_of_region_use":
            fraud_prob = 0.82
            signal_count = 2
            confidence = 0.85
        elif pattern == "card_not_present_new_device":
            fraud_prob = 0.78
            signal_count = 2
            confidence = 0.80
        elif initial_score < 0.20:
            fraud_prob = 0.12
            signal_count = 2
            confidence = 0.85
        else:
            # Single ambiguous signal
            fraud_prob = initial_score if initial_score < 0.70 else 0.65
            signal_count = 1
            confidence = 0.60

        # Verdict
        if fraud_prob >= 0.70:
            verdict = "fraud"
        elif fraud_prob <= 0.20:
            verdict = "legitimate"
        else:
            verdict = "uncertain"

        updates = {
            "step_count": step,
            "exposure_usd": round(exposure, 2),
            "fraud_probability": round(fraud_prob, 2),
            "confidence": round(confidence, 2),
            "signal_count": signal_count,
            "verdict": verdict
        }
        updates["telemetry"] = self._log_telemetry(
            state,
            node="risk_assessor",
            action="assess_risk",
            details={"fraud_probability": fraud_prob, "exposure_usd": exposure, "verdict": verdict}
        )
        return updates

    # -------------------------------------------------------------------------
    # Node 6: sufficiency_evaluator
    # -------------------------------------------------------------------------
    def node_sufficiency_evaluator(self, state: InvestigationState) -> Dict[str, Any]:
        """Evaluates whether evidence satisfies stopping criteria or requires simulated verification."""
        step = state.get("step_count", 5) + 1
        fraud_prob = state.get("fraud_probability", 0.5)
        signal_count = state.get("signal_count", 1)
        trigger_type = state.get("trigger_type", "risk_score")
        pattern = state.get("pattern", "none")
        evidence_requests = list(state.get("evidence_requests", []))
        evidence = list(state.get("evidence", []))
        customer_verified = state.get("customer_verified")

        # Section 5: Deterministic simulation of evidence requests if not yet asked
        if customer_verified is None:
            if trigger_type == "customer_report":
                resp = "Customer reported unrecognized transaction on card."
                customer_verified = False
                fraud_prob = 0.89
                verdict = "fraud"
            elif pattern == "card_testing":
                resp = "Customer states they did not make these micro-authorizations and retains the physical card."
                customer_verified = False
                fraud_prob = 0.92
                verdict = "fraud"
            elif fraud_prob < 0.40:
                resp = "Customer confirmed they authorized the transaction."
                customer_verified = True
                fraud_prob = 0.08
                verdict = "legitimate"
            else:
                resp = "Customer denies making the purchase and confirms card retained in possession."
                customer_verified = False
                fraud_prob = max(0.86, fraud_prob)
                verdict = "fraud"

            evidence_requests.append({
                "type": "customer_validation",
                "asked_after_step": step,
                "assumed_response": resp
            })
            evidence.append({
                "claim": resp,
                "source": "customer",
                "ref": f"evidence_request:{len(evidence_requests)}",
                "entity_ids": []
            })
        else:
            verdict = state.get("verdict", "uncertain")

        # Section 6: Stopping Criteria
        should_stop = False
        stop_reason = ""

        if fraud_prob >= 0.85 and signal_count >= 2:
            should_stop = True
            stop_reason = f"Fraud probability {fraud_prob:.2f} >= 0.85 supported by {signal_count} independent evidence signals (Section 6)"
        elif fraud_prob <= 0.15 and signal_count >= 2:
            should_stop = True
            stop_reason = f"Fraud probability {fraud_prob:.2f} <= 0.15 supported by {signal_count} independent evidence signals (Section 6)"
        elif customer_verified is True:
            should_stop = True
            stop_reason = "Customer confirmation settled the investigation as legitimate (Section 6)"
        elif customer_verified is False and fraud_prob >= 0.70:
            should_stop = True
            stop_reason = "Customer denial confirmed unauthorized activity (Section 6)"
        elif step >= state.get("max_steps", 10):
            should_stop = True
            stop_reason = f"Reached maximum allowed steps ({state.get('max_steps', 10)}) (Section 6)"
        else:
            should_stop = True
            stop_reason = "Further steps unlikely to change decision (Section 6)"

        updates = {
            "step_count": step,
            "evidence_requests": evidence_requests,
            "evidence": evidence,
            "customer_verified": customer_verified,
            "fraud_probability": round(fraud_prob, 2),
            "verdict": verdict,
            "should_stop": should_stop,
            "stop_reason": stop_reason
        }
        updates["telemetry"] = self._log_telemetry(
            state,
            node="sufficiency_evaluator",
            action="evaluate_sufficiency",
            details={"should_stop": should_stop, "stop_reason": stop_reason}
        )
        return updates

    # -------------------------------------------------------------------------
    # Node 7: policy_evaluator
    # -------------------------------------------------------------------------
    def node_policy_evaluator(self, state: InvestigationState) -> Dict[str, Any]:
        """Invokes Phase 5 PolicyEngine to determine policy-compliant Next-Best-Actions and SAR."""
        step = state.get("step_count", 6) + 1

        # Initial context (before evidence response)
        initial_ctx = InvestigationContext(
            fraud_probability=float(state.get("fraud_probability", 0.5)),
            exposure_usd=float(state.get("exposure_usd", 0.0)),
            signal_count=int(state.get("signal_count", 1)),
            verdict=str(state.get("verdict", "uncertain")),
            flagged_txn_id=state.get("flagged_txn_id"),
            card_id=state.get("card_id"),
            customer_id=state.get("customer_id"),
            single_signal_only=(state.get("signal_count", 1) == 1),
            customer_verified=None,
            card_testing_detected=(state.get("pattern") == "card_testing"),
            testing_txns=state.get("affected_txn_ids", []),
            larger_purchase_cleared=(float(state.get("exposure_usd", 0.0)) > 100.0),
            shared_device_cards=state.get("connected_card_ids", []),
            undocumented_pattern_detected=(state.get("pattern") == "undocumented")
        )

        # Final context (after simulated response)
        final_ctx = InvestigationContext(
            fraud_probability=float(state.get("fraud_probability", 0.5)),
            exposure_usd=float(state.get("exposure_usd", 0.0)),
            signal_count=int(state.get("signal_count", 1)),
            verdict=str(state.get("verdict", "uncertain")),
            flagged_txn_id=state.get("flagged_txn_id"),
            card_id=state.get("card_id"),
            customer_id=state.get("customer_id"),
            single_signal_only=False,
            customer_verified=state.get("customer_verified"),
            card_testing_detected=(state.get("pattern") == "card_testing"),
            testing_txns=state.get("affected_txn_ids", []),
            larger_purchase_cleared=(float(state.get("exposure_usd", 0.0)) > 100.0),
            shared_device_cards=state.get("connected_card_ids", []),
            undocumented_pattern_detected=(state.get("pattern") == "undocumented")
        )

        decision = self.policy_engine.decide(initial_ctx, final_ctx)
        initial_nba = self.policy_engine.format_nba(decision.initial_actions)
        final_nba = self.policy_engine.format_nba(decision.final_actions)

        # Build SAR narrative and schema
        file_sar = decision.should_file_report
        sar_reason = "Policy R2/R6: confirmed fraud with qualifying exposure/shared entity" if file_sar else "Policy does not require filing a Suspicious Activity Report"
        sar_narrative = ""
        sar_subjects = []
        sar_dates = []

        if file_sar:
            tx = state.get("transaction_details", {}).get("transaction", {}) or {}
            txn_date = str(tx.get("ts", "2016-11-01"))[:10]
            sar_dates = [txn_date, txn_date]
            sar_subjects = [state.get("customer_id", ""), state.get("card_id", "")]
            if state.get("connected_card_ids"):
                sar_subjects.extend(state.get("connected_card_ids", []))
            sar_subjects = [s for s in sar_subjects if s]

            sar_narrative = (
                f"Between {sar_dates[0]} and {sar_dates[1]}, suspicious transaction activity totaling ${state.get('exposure_usd', 0.0):.2f} "
                f"was identified on card {state.get('card_id')} owned by customer {state.get('customer_id')}. "
                f"Activity matched the '{state.get('pattern')}' typology. The primary transaction was conducted via the {tx.get('channel', 'online')} channel. "
                f"The cardholder verified unauthorized activity. The compromise connects to {len(state.get('connected_card_ids', []))} other card(s) through shared device profiles. "
                f"Immediate mitigation including card blocking and downstream monitoring was enacted in accordance with bank policy."
            )

        sar_data: SARDict = {
            "file": file_sar,
            "reason": sar_reason,
            "narrative": sar_narrative,
            "subjects": sar_subjects,
            "total_amount_usd": float(state.get("exposure_usd", 0.0)) if file_sar else 0.0,
            "activity_dates": sar_dates
        }

        # Case status
        verdict = state.get("verdict", "uncertain")
        if verdict == "fraud":
            status = "closed_fraud"
        elif verdict == "legitimate":
            status = "closed_legitimate"
        else:
            status = "escalated"

        summary = (
            f"Investigation {state.get('case_id')} closed with verdict '{verdict}' and pattern '{state.get('pattern')}'. "
            f"Total assessed exposure is ${state.get('exposure_usd', 0.0):.2f} with assessed fraud probability of {state.get('fraud_probability', 0.0):.2f}. "
            f"{'A Suspicious Activity Report (SAR) was prepared for regulatory submission.' if file_sar else 'No SAR filing required.'}"
        )

        updates = {
            "step_count": step,
            "initial_actions": initial_nba,
            "final_actions": final_nba,
            "what_changed": decision.what_changed,
            "next_best_actions": {
                "initial": initial_nba,
                "final": final_nba,
                "what_changed": decision.what_changed
            },
            "sar": sar_data,
            "status": status,
            "summary": summary
        }
        updates["telemetry"] = self._log_telemetry(
            state,
            node="policy_evaluator",
            action="evaluate_policy",
            details={"file_sar": file_sar, "status": status, "what_changed": decision.what_changed}
        )
        return updates

    # -------------------------------------------------------------------------
    # Node 8: case_updater
    # -------------------------------------------------------------------------
    def node_case_updater(self, state: InvestigationState) -> Dict[str, Any]:
        """Persists closed case into graph memory and records execution status."""
        step = state.get("step_count", 7) + 1
        case_id = state.get("case_id", "CASE-UNKNOWN")

        write_res = self.mcp.write_case_to_graph(
            case_id=case_id,
            customer_id=state.get("customer_id", ""),
            card_id=state.get("card_id", ""),
            outcome="confirmed_fraud" if state.get("verdict") == "fraud" else ("cleared" if state.get("verdict") == "legitimate" else "uncertain"),
            pattern=state.get("pattern", "none"),
            exposure_usd=float(state.get("exposure_usd", 0.0)),
            txn_ids=state.get("affected_txn_ids", []),
            connected_card_ids=state.get("connected_card_ids", []),
            actions_taken=[a["action"] for a in state.get("final_actions", [])],
            report_filed=state.get("sar", {}).get("file", False),
            analyst_notes=state.get("summary", "")
        )

        write_mode = write_res.get("execution_mode", "offline_simulated")
        written = write_res.get("status") == "success"

        updates = {
            "step_count": step,
            "written_to_graph": written,
            "graph_case_id": case_id,
            "graph_write_mode": write_mode
        }
        updates["telemetry"] = self._log_telemetry(
            state,
            node="case_updater",
            action="persist_case",
            details={"written": written, "graph_write_mode": write_mode}
        )
        return updates

    # -------------------------------------------------------------------------
    # Public Execution Method
    # -------------------------------------------------------------------------
    def run(self, input_case: Dict[str, Any]) -> InvestigationState:
        """Runs the LangGraph agent for a single investigation case."""
        t0 = time.time()
        initial_state: InvestigationState = {
            "case_id": input_case.get("case_id", "HHG-UNKNOWN"),
            "opened_at": input_case.get("opened_at", datetime.now().isoformat()),
            "trigger_type": input_case.get("trigger_type", "risk_score"),
            "trigger_text": input_case.get("trigger_text", ""),
            "flagged_txn_id": str(input_case.get("flagged_txn_id", "")),
            "card_id": str(input_case.get("card_id", "")),
            "customer_id": str(input_case.get("customer_id", "")),
            "initial_risk_score": float(input_case.get("risk_score", 0.5)) if input_case.get("risk_score") is not None else None,
            "step_count": 0,
            "max_steps": input_case.get("max_steps", 10),
            "telemetry": [],
            "errors": []
        }

        final_state = self.graph.invoke(initial_state)
        final_state["latency_s"] = round(time.time() - t0, 3)
        return final_state

    def format_answer_file(self, state: InvestigationState) -> Dict[str, Any]:
        """Formats the final InvestigationState into the exact required 3-part JSON output."""
        return {
            "case_id": state.get("case_id", ""),
            "case": {
                "status": state.get("status", "open"),
                "verdict": state.get("verdict", "uncertain"),
                "fraud_probability": state.get("fraud_probability", 0.0),
                "pattern": state.get("pattern", "none"),
                "pattern_description": state.get("pattern_description", ""),
                "affected_txn_ids": state.get("affected_txn_ids", []),
                "first_suspicious_txn_id": state.get("first_suspicious_txn_id", ""),
                "connected_card_ids": state.get("connected_card_ids", []),
                "connected_device_profiles": state.get("connected_device_profiles", []),
                "exposure_usd": state.get("exposure_usd", 0.0),
                "evidence": state.get("evidence", []),
                "similar_prior_cases": state.get("similar_prior_cases", []),
                "summary": state.get("summary", ""),
                "written_to_graph": state.get("written_to_graph", False),
                "graph_case_id": state.get("graph_case_id", "")
            },
            "evidence_requests": state.get("evidence_requests", []),
            "next_best_actions": state.get("next_best_actions", {
                "initial": state.get("initial_actions", []),
                "final": state.get("final_actions", []),
                "what_changed": state.get("what_changed", "nothing")
            }),
            "sar": state.get("sar", {
                "file": False,
                "reason": "",
                "narrative": "",
                "subjects": [],
                "total_amount_usd": 0.0,
                "activity_dates": []
            }),
            "stop_reason": state.get("stop_reason", ""),
            "tool_calls": state.get("tool_calls", 0),
            "tokens": state.get("tokens", 0),
            "latency_s": state.get("latency_s", 0.0)
        }
