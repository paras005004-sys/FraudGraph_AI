"""
Tests for Phase 6 — LangGraph Stateful Investigation Agent Orchestrator
========================================================================
Covers:
1. Valid investigation initialization
2. State transitions through the graph
3. Phase 4 tool integration
4. Phase 5 GraphRAG integration
5. Policy engine integration
6. Stopping at probability >= 0.85
7. Stopping at probability <= 0.15
8. Stopping after verification response
9. Stopping at maximum steps
10. Telemetry generation
11. Offline TigerGraph fallback
12. Missing evidence handling
13. Malformed input handling
14. Case update/write-back behavior
15. No fabricated evidence
16. Final state and answer file schema validation
"""

import unittest
from pathlib import Path
from src.agent.orchestrator import FraudInvestigationOrchestrator
from src.agent.state import InvestigationState
from src.data.config import DataPipelineConfig
from src.data.loaders import DataLoader


class TestAgentOrchestration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = DataPipelineConfig()
        cls.loader = DataLoader(cls.config)
        cls.case_pack_df = cls.loader.load_case_pack()
        cls.orchestrator = FraudInvestigationOrchestrator()

        # Benchmark sample 1 (HHG-001)
        row0 = cls.case_pack_df.iloc[0]
        cls.sample_case_001 = {
            "case_id": str(row0["case_id"]),
            "opened_at": str(row0["opened_at"]),
            "trigger_type": str(row0["trigger_type"]),
            "trigger_text": str(row0["trigger_text"]),
            "flagged_txn_id": str(row0["flagged_txn_id"]),
            "card_id": str(row0["card_id"]),
            "customer_id": str(row0["customer_id"]),
            "risk_score": float(row0["risk_score"]) if str(row0["risk_score"]) != "nan" else None
        }

    # 1. Valid investigation initialization
    def test_investigation_initialization(self):
        state = self.orchestrator.node_trigger_handler(self.sample_case_001)
        self.assertEqual(state["case_id"], self.sample_case_001["case_id"])
        self.assertEqual(state["step_count"], 1)
        self.assertFalse(state["should_stop"])
        self.assertEqual(len(state["errors"]), 0)

    # 2. State transitions through the graph
    def test_full_pipeline_execution(self):
        final_state = self.orchestrator.run(self.sample_case_001)
        self.assertIn("status", final_state)
        self.assertIn("verdict", final_state)
        self.assertIn("next_best_actions", final_state)
        self.assertIn("sar", final_state)
        self.assertTrue(final_state["should_stop"])
        self.assertGreater(final_state["step_count"], 6)

    # 3. Phase 4 tool integration
    def test_phase4_tool_integration(self):
        final_state = self.orchestrator.run(self.sample_case_001)
        self.assertGreaterEqual(final_state["tool_calls"], 7)
        self.assertIsNotNone(final_state.get("transaction_details"))
        self.assertIsNotNone(final_state.get("card_history"))
        self.assertIsNotNone(final_state.get("connected_entities"))

    # 4. Phase 5 GraphRAG integration
    def test_phase5_rag_integration(self):
        final_state = self.orchestrator.run(self.sample_case_001)
        self.assertIn("similar_prior_cases", final_state)
        self.assertIsInstance(final_state["similar_prior_cases"], list)
        self.assertGreater(len(final_state["similar_prior_cases"]), 0)

    # 5. Policy engine integration
    def test_policy_engine_integration(self):
        final_state = self.orchestrator.run(self.sample_case_001)
        nba = final_state.get("next_best_actions", {})
        self.assertIn("initial", nba)
        self.assertIn("final", nba)
        self.assertIn("what_changed", nba)
        self.assertGreater(len(nba["final"]), 0)
        # Check approval route valid
        for a in nba["final"]:
            self.assertIn(a["route"], ["auto", "L1", "L2"])

    # 6. Stopping at probability >= 0.85
    def test_stopping_at_high_probability(self):
        mock_case = dict(self.sample_case_001)
        mock_case["trigger_type"] = "customer_report"
        final_state = self.orchestrator.run(mock_case)
        self.assertTrue(final_state["should_stop"])
        self.assertGreaterEqual(final_state["fraud_probability"], 0.85)
        self.assertIn("Section 6", final_state["stop_reason"])

    # 7. Stopping at probability <= 0.15
    def test_stopping_at_low_probability(self):
        mock_case = dict(self.sample_case_001)
        mock_case["risk_score"] = 0.05
        final_state = self.orchestrator.run(mock_case)
        self.assertTrue(final_state["should_stop"])
        self.assertIn("Section 6", final_state["stop_reason"])

    # 8. Stopping after verification response
    def test_stopping_after_verification_response(self):
        final_state = self.orchestrator.run(self.sample_case_001)
        self.assertTrue(final_state["should_stop"])
        self.assertIsNotNone(final_state.get("customer_verified"))
        self.assertIn("Section 6", final_state["stop_reason"])

    # 9. Stopping at maximum steps
    def test_stopping_at_maximum_steps(self):
        mock_case = dict(self.sample_case_001)
        mock_case["max_steps"] = 3
        # Direct check on sufficiency evaluator with step exceeding max_steps
        state: InvestigationState = {
            "step_count": 4,
            "max_steps": 3,
            "fraud_probability": 0.50,
            "signal_count": 1,
            "customer_verified": False,
            "evidence_requests": [],
            "evidence": []
        }
        res = self.orchestrator.node_sufficiency_evaluator(state)
        self.assertTrue(res["should_stop"])

    # 10. Telemetry generation
    def test_telemetry_generation(self):
        final_state = self.orchestrator.run(self.sample_case_001)
        telemetry = final_state.get("telemetry", [])
        self.assertGreater(len(telemetry), 6)
        nodes_logged = [t["node"] for t in telemetry]
        for expected in ["trigger_handler", "evidence_gatherer", "pattern_matcher", "rag_retriever", "risk_assessor", "policy_evaluator", "case_updater"]:
            self.assertIn(expected, nodes_logged)

    # 11. Offline TigerGraph fallback
    def test_offline_tigergraph_fallback(self):
        final_state = self.orchestrator.run(self.sample_case_001)
        self.assertTrue(final_state.get("written_to_graph"))
        self.assertEqual(final_state.get("graph_write_mode"), "offline_simulated")

    # 12. Missing evidence handling
    def test_missing_evidence_handling(self):
        missing_case = {
            "case_id": "TEST-MISSING-001",
            "flagged_txn_id": "999999999",
            "card_id": "NONEXISTENT-K1",
            "customer_id": "C99999",
            "trigger_type": "risk_score"
        }
        final_state = self.orchestrator.run(missing_case)
        self.assertIn("status", final_state)
        self.assertGreater(len(final_state.get("errors", [])), 0)
        self.assertTrue(final_state.get("should_stop"))

    # 13. Malformed input handling
    def test_malformed_input_handling(self):
        malformed_case = {
            "case_id": "",
            "flagged_txn_id": None,
            "card_id": None
        }
        final_state = self.orchestrator.run(malformed_case)
        self.assertGreater(len(final_state.get("errors", [])), 0)

    # 14. Case update/write-back behavior
    def test_case_writeback_behavior(self):
        final_state = self.orchestrator.run(self.sample_case_001)
        self.assertTrue(final_state["written_to_graph"])
        self.assertEqual(final_state["graph_case_id"], self.sample_case_001["case_id"])

    # 15. No fabricated evidence
    def test_no_fabricated_evidence(self):
        final_state = self.orchestrator.run(self.sample_case_001)
        for ev in final_state.get("evidence", []):
            self.assertIn("claim", ev)
            self.assertIn("source", ev)
            self.assertIn(ev["source"], ["graph", "document", "customer", "external"])
            self.assertIn("ref", ev)

    # 16. Answer file schema validation
    def test_format_answer_file_schema(self):
        final_state = self.orchestrator.run(self.sample_case_001)
        answer = self.orchestrator.format_answer_file(final_state)

        # Top level keys
        for key in ["case_id", "case", "evidence_requests", "next_best_actions", "sar", "stop_reason", "tool_calls", "tokens", "latency_s"]:
            self.assertIn(key, answer, f"Missing top-level key {key}")

        # Part 1: case
        c = answer["case"]
        for key in ["status", "verdict", "fraud_probability", "pattern", "pattern_description", "affected_txn_ids", "first_suspicious_txn_id", "connected_card_ids", "connected_device_profiles", "exposure_usd", "evidence", "similar_prior_cases", "summary", "written_to_graph", "graph_case_id"]:
            self.assertIn(key, c, f"Missing case key {key}")

        # Part 2: sar
        sar = answer["sar"]
        for key in ["file", "reason", "narrative", "subjects", "total_amount_usd", "activity_dates"]:
            self.assertIn(key, sar, f"Missing sar key {key}")

        # Part 3: next_best_actions
        nba = answer["next_best_actions"]
        for key in ["initial", "final", "what_changed"]:
            self.assertIn(key, nba, f"Missing nba key {key}")


if __name__ == "__main__":
    unittest.main()
