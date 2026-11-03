"""
Tests for Phase 7 — Benchmark Evaluation & Answer File Validation
==================================================================
Tests:
1. All 20 case IDs discovered in case_pack.csv
2. Answer file generation in cases/
3. JSON syntax validity across all 20 files
4. Schema conformance (case, sar, next_best_actions, evidence_requests)
5. Case ID and transaction ID consistency
6. Provenance compliance (source in graph, document, customer, external)
7. SAR structure and narrative requirements
8. NBA action, route, and reason requirements
9. Benchmark runner metric computation
10. Uncomputable metric handling (ground truth accuracy)
"""

import json
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = PROJECT_ROOT / "cases"
REPORTS_DIR = PROJECT_ROOT / "reports"
DATASET_DIR = PROJECT_ROOT / "dataset" / "HHGOA_IEEE"


class TestBenchmarkEvaluation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        case_pack_path = DATASET_DIR / "case_pack.csv"
        cls.case_pack_df = pd.read_csv(case_pack_path)
        cls.expected_case_ids = cls.case_pack_df["case_id"].astype(str).tolist()

    # 1. 20 case IDs discovered
    def test_twenty_case_ids_discovered(self):
        self.assertEqual(len(self.expected_case_ids), 20)
        for i in range(1, 21):
            expected_cid = f"HHG-{i:03d}"
            self.assertIn(expected_cid, self.expected_case_ids)

    # 2. Answer files present
    def test_answer_files_present(self):
        found_files = list(CASES_DIR.glob("HHG-*.json"))
        found_cids = {f.stem for f in found_files}
        for cid in self.expected_case_ids:
            self.assertIn(cid, found_cids, f"Missing answer file for {cid}")

    # 3. JSON validity
    def test_json_validity(self):
        for cid in self.expected_case_ids:
            fpath = CASES_DIR / f"{cid}.json"
            self.assertTrue(fpath.exists(), f"File {fpath} does not exist")
            with open(fpath, "r", encoding="utf-8") as fh:
                try:
                    data = json.load(fh)
                except Exception as e:
                    self.fail(f"Invalid JSON in {cid}.json: {e}")
                self.assertIsInstance(data, dict)

    # 4. Schema conformance
    def test_schema_top_level_and_nested_fields(self):
        required_top = {"case_id", "case", "evidence_requests", "next_best_actions", "sar", "stop_reason", "tool_calls", "tokens", "latency_s"}
        required_case = {"status", "verdict", "fraud_probability", "pattern", "pattern_description", "affected_txn_ids", "first_suspicious_txn_id", "connected_card_ids", "connected_device_profiles", "exposure_usd", "evidence", "similar_prior_cases", "summary", "written_to_graph", "graph_case_id"}
        required_sar = {"file", "reason", "narrative", "subjects", "total_amount_usd", "activity_dates"}
        required_nba = {"initial", "final", "what_changed"}

        for cid in self.expected_case_ids:
            fpath = CASES_DIR / f"{cid}.json"
            with open(fpath, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            self.assertTrue(required_top.issubset(set(data.keys())), f"{cid} missing top-level keys: {required_top - set(data.keys())}")
            self.assertTrue(required_case.issubset(set(data["case"].keys())), f"{cid} missing case keys: {required_case - set(data['case'].keys())}")
            self.assertTrue(required_sar.issubset(set(data["sar"].keys())), f"{cid} missing sar keys: {required_sar - set(data['sar'].keys())}")
            self.assertTrue(required_nba.issubset(set(data["next_best_actions"].keys())), f"{cid} missing nba keys: {required_nba - set(data['next_best_actions'].keys())}")

    # 5. Case ID and Transaction ID consistency
    def test_case_id_and_flagged_txn_consistency(self):
        txn_lookup = dict(zip(self.case_pack_df["case_id"].astype(str), self.case_pack_df["flagged_txn_id"].astype(str)))
        for cid in self.expected_case_ids:
            fpath = CASES_DIR / f"{cid}.json"
            with open(fpath, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            self.assertEqual(data["case_id"], cid)
            expected_txn = txn_lookup.get(cid)
            case_p = data["case"]
            if case_p["verdict"] == "fraud" and expected_txn:
                affected = [str(x) for x in case_p["affected_txn_ids"]]
                self.assertIn(expected_txn, affected, f"Flagged txn {expected_txn} not in affected_txn_ids for {cid}")

    # 6. Provenance compliance
    def test_evidence_provenance_compliance(self):
        valid_sources = {"graph", "document", "customer", "external"}
        for cid in self.expected_case_ids:
            fpath = CASES_DIR / f"{cid}.json"
            with open(fpath, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            evidence = data["case"]["evidence"]
            self.assertIsInstance(evidence, list)
            for ev in evidence:
                self.assertIn("claim", ev)
                self.assertIn("source", ev)
                self.assertIn(ev["source"], valid_sources)
                self.assertIn("ref", ev)
                self.assertIn("entity_ids", ev)
                self.assertIsInstance(ev["entity_ids"], list)

    # 7. SAR structure
    def test_sar_structure_compliance(self):
        for cid in self.expected_case_ids:
            fpath = CASES_DIR / f"{cid}.json"
            with open(fpath, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            sar = data["sar"]
            self.assertIsInstance(sar["file"], bool)
            if sar["file"]:
                self.assertGreater(len(sar["narrative"]), 20)
                self.assertGreater(len(sar["subjects"]), 0)
                self.assertGreater(sar["total_amount_usd"], 0.0)
                self.assertEqual(len(sar["activity_dates"]), 2)
            else:
                self.assertEqual(sar["narrative"], "")
                self.assertEqual(sar["subjects"], [])
                self.assertEqual(sar["total_amount_usd"], 0.0)
                self.assertEqual(sar["activity_dates"], [])

    # 8. NBA action, route, and reason
    def test_nba_routes_and_fields(self):
        valid_routes = {"auto", "L1", "L2"}
        for cid in self.expected_case_ids:
            fpath = CASES_DIR / f"{cid}.json"
            with open(fpath, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            nba = data["next_best_actions"]
            self.assertIsInstance(nba["initial"], list)
            self.assertIsInstance(nba["final"], list)
            self.assertIsInstance(nba["what_changed"], str)

            for act in nba["final"]:
                self.assertIn("action", act)
                self.assertIn("route", act)
                self.assertIn("reason", act)
                self.assertIn(act["route"], valid_routes)

    # 9. Benchmark report file generated
    def test_benchmark_report_json_exists(self):
        report_path = REPORTS_DIR / "benchmark_results.json"
        self.assertTrue(report_path.exists(), "benchmark_results.json not generated")
        with open(report_path, "r", encoding="utf-8") as fh:
            bench = json.load(fh)
        self.assertIn("plain_rag", bench)
        self.assertIn("graphrag", bench)
        self.assertIn("agentic_graphrag", bench)
        self.assertIn("metrics_summary", bench)

    # 10. Uncomputable metric explicitly reported
    def test_uncomputable_metric_handled_honestly(self):
        report_path = REPORTS_DIR / "benchmark_results.json"
        with open(report_path, "r", encoding="utf-8") as fh:
            bench = json.load(fh)
        summary = bench["metrics_summary"]
        self.assertIn("uncomputable_metrics", summary)
        self.assertGreater(len(summary["uncomputable_metrics"]), 0)


if __name__ == "__main__":
    unittest.main()
