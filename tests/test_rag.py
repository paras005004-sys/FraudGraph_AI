"""
Tests for Phase 5B & 5C — Vector Store and Hybrid GraphRAG Retriever
=====================================================================
Tests cover:
  - VectorStore: indexing counts, retrieval, metadata, empty query, source_type filter
  - Retriever: graph evidence, vector evidence, hybrid, provenance, no fabricated evidence
"""
import unittest
from pathlib import Path
from src.rag.vector_store import FraudVectorStore, Document, SearchResult
from src.rag.retriever import HybridGraphRAGRetriever, EvidenceItem
from src.data.config import DataPipelineConfig
from src.data.loaders import DataLoader


class TestVectorStore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store = FraudVectorStore(data_dir=Path("dataset/HHGOA_IEEE"))

    def test_closed_cases_indexed(self):
        stats = self.store.stats()
        self.assertEqual(stats["closed_case"], 5565,
                         f"Expected 5565 closed cases, got {stats['closed_case']}")

    def test_fraud_patterns_indexed(self):
        stats = self.store.stats()
        self.assertEqual(stats["fraud_pattern"], 5,
                         f"Expected 5 fraud patterns, got {stats['fraud_pattern']}")

    def test_regulatory_refs_indexed(self):
        stats = self.store.stats()
        self.assertEqual(stats["regulatory"], 10,
                         f"Expected 10 regulatory references, got {stats['regulatory']}")

    def test_policy_rules_indexed(self):
        stats = self.store.stats()
        self.assertEqual(stats["policy_rule"], 10,
                         f"Expected 10 policy rules (R1-R10), got {stats['policy_rule']}")

    def test_total_documents(self):
        stats = self.store.stats()
        expected = 5565 + 5 + 10 + 10
        self.assertEqual(stats["total"], expected,
                         f"Expected {expected} total docs, got {stats['total']}")

    def test_retrieval_returns_results(self):
        results = self.store.query("card testing small authorizations online fraud", n=5)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 5)

    def test_retrieval_returns_search_result_objects(self):
        results = self.store.query("out of region billing address", n=3)
        for r in results:
            self.assertIsInstance(r, SearchResult)
            self.assertIsInstance(r.doc, Document)
            self.assertIsInstance(r.score, float)
            self.assertGreaterEqual(r.score, 0.0)
            self.assertLessEqual(r.score, 1.0)

    def test_retrieval_scores_ordered_descending(self):
        results = self.store.query("account takeover device anomaly", n=10)
        scores = [r.score for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_metadata_preserved_closed_case(self):
        results = self.store.query("confirmed fraud card not present", n=5,
                                   source_types=["closed_case"])
        for r in results:
            meta = r.doc.metadata
            self.assertIn("case_id", meta)
            self.assertIn("outcome", meta)
            self.assertIn("pattern", meta)
            self.assertIn("card_id", meta)
            self.assertIn("customer_id", meta)
            self.assertEqual(meta["source_type"], "closed_case")

    def test_metadata_preserved_fraud_pattern(self):
        results = self.store.query("card testing authorizations", n=3,
                                   source_types=["fraud_pattern"])
        self.assertGreater(len(results), 0)
        for r in results:
            meta = r.doc.metadata
            self.assertIn("pattern_id", meta)
            self.assertIn("name", meta)
            self.assertIn("policy_rule", meta)
            self.assertEqual(meta["source_type"], "fraud_pattern")

    def test_metadata_preserved_regulatory(self):
        results = self.store.query("SAR narrative suspicious activity report", n=3,
                                   source_types=["regulatory"])
        self.assertGreater(len(results), 0)
        for r in results:
            meta = r.doc.metadata
            self.assertIn("ref_id", meta)
            self.assertIn("ref_name", meta)
            self.assertIn("agency", meta)
            self.assertIn("url", meta)
            self.assertEqual(meta["source_type"], "regulatory")

    def test_metadata_preserved_policy_rule(self):
        results = self.store.query("verify before block weak signal", n=3,
                                   source_types=["policy_rule"])
        self.assertGreater(len(results), 0)
        for r in results:
            meta = r.doc.metadata
            self.assertIn("rule_id", meta)
            self.assertEqual(meta["source_type"], "policy_rule")

    def test_empty_query_returns_empty_list(self):
        results = self.store.query("")
        self.assertEqual(results, [])

    def test_whitespace_only_query_returns_empty(self):
        results = self.store.query("   ")
        self.assertEqual(results, [])

    def test_source_type_filter_closed_case_only(self):
        results = self.store.query("fraud card block", n=10, source_types=["closed_case"])
        for r in results:
            self.assertEqual(r.doc.source_type, "closed_case")

    def test_source_type_filter_pattern_only(self):
        results = self.store.query("online purchase device", n=5, source_types=["fraud_pattern"])
        for r in results:
            self.assertEqual(r.doc.source_type, "fraud_pattern")

    def test_source_type_filter_regulatory_only(self):
        results = self.store.query("SAR filing FinCEN", n=5, source_types=["regulatory"])
        for r in results:
            self.assertEqual(r.doc.source_type, "regulatory")

    def test_source_type_filter_policy_rule_only(self):
        results = self.store.query("block card exposure", n=5, source_types=["policy_rule"])
        for r in results:
            self.assertEqual(r.doc.source_type, "policy_rule")

    def test_get_by_id_policy_rule(self):
        doc = self.store.get_by_id("rule::R5")
        self.assertIsNotNone(doc)
        self.assertEqual(doc.metadata["rule_id"], "R5")

    def test_get_by_id_fraud_pattern(self):
        doc = self.store.get_by_id("pattern::card_testing")
        self.assertIsNotNone(doc)
        self.assertEqual(doc.metadata["pattern_id"], "card_testing")

    def test_get_by_id_regulatory(self):
        doc = self.store.get_by_id("reg::fincen-sar-narrative-guidance")
        self.assertIsNotNone(doc)
        self.assertEqual(doc.metadata["agency"], "FinCEN")

    def test_get_by_id_not_found(self):
        doc = self.store.get_by_id("nonexistent::XYZ")
        self.assertIsNone(doc)

    def test_card_testing_pattern_top_result_for_card_testing_query(self):
        results = self.store.query(
            "three small online authorizations under five dollars card testing",
            n=3, source_types=["fraud_pattern"]
        )
        self.assertGreater(len(results), 0)
        top_pattern = results[0].doc.metadata.get("pattern_id")
        self.assertEqual(top_pattern, "card_testing",
                         f"Expected card_testing as top match, got {top_pattern}")

    def test_r1_top_result_for_verify_query(self):
        results = self.store.query(
            "verify before block single signal probability below 0.70",
            n=3, source_types=["policy_rule"]
        )
        self.assertGreater(len(results), 0)
        top_rule = results[0].doc.metadata.get("rule_id")
        self.assertEqual(top_rule, "R1",
                         f"Expected R1 as top match, got {top_rule}")


class TestHybridRetriever(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = DataPipelineConfig()
        cls.loader = DataLoader(cls.config)
        cls.case_pack_df = cls.loader.load_case_pack()
        row0 = cls.case_pack_df.iloc[0]
        cls.sample_txn_id = str(row0["flagged_txn_id"])
        cls.sample_card_id = str(row0["card_id"])
        cls.sample_cust_id = str(row0["customer_id"])

        cls.store = FraudVectorStore(data_dir=Path("dataset/HHGOA_IEEE"))
        cls.retriever = HybridGraphRAGRetriever(vector_store=cls.store)

    def test_retrieve_returns_result_object(self):
        from src.rag.retriever import HybridRetrievalResult
        result = self.retriever.retrieve(
            txn_id=self.sample_txn_id,
            card_id=self.sample_card_id,
            customer_id=self.sample_cust_id
        )
        self.assertIsInstance(result, HybridRetrievalResult)

    def test_retrieve_graph_evidence_present(self):
        result = self.retriever.retrieve(
            txn_id=self.sample_txn_id,
            card_id=self.sample_card_id
        )
        # Transaction details must be present
        self.assertIsNotNone(result.transaction_details)
        # Card history must be present
        self.assertIsNotNone(result.card_history_summary)

    def test_retrieve_evidence_items_nonempty(self):
        result = self.retriever.retrieve(
            txn_id=self.sample_txn_id,
            card_id=self.sample_card_id
        )
        self.assertGreater(len(result.evidence_items), 0)

    def test_every_evidence_item_has_provenance(self):
        result = self.retriever.retrieve(
            txn_id=self.sample_txn_id,
            card_id=self.sample_card_id
        )
        for item in result.evidence_items:
            self.assertIsInstance(item, EvidenceItem)
            self.assertTrue(item.claim and len(item.claim) > 0,
                            "Evidence item missing claim")
            self.assertIn(item.source, ("graph", "document", "customer", "external"),
                          f"Unknown source type: {item.source}")
            self.assertTrue(item.ref and len(item.ref) > 0,
                            "Evidence item missing ref")

    def test_retrieve_vector_evidence_present(self):
        result = self.retriever.retrieve(
            txn_id=self.sample_txn_id,
            card_id=self.sample_card_id,
            query_hint="card testing online fraud"
        )
        # Should have some similar cases from vector store
        self.assertIsInstance(result.similar_prior_cases, list)
        self.assertIsInstance(result.relevant_patterns, list)

    def test_format_evidence_exact_schema(self):
        result = self.retriever.retrieve(
            txn_id=self.sample_txn_id,
            card_id=self.sample_card_id
        )
        formatted = self.retriever.format_evidence(result)
        for item in formatted:
            self.assertIn("claim", item)
            self.assertIn("source", item)
            self.assertIn("ref", item)
            self.assertIn("entity_ids", item)
            self.assertIsInstance(item["entity_ids"], list)

    def test_no_fabricated_transaction_ids(self):
        """All transaction entity_ids in graph evidence must exist in graph."""
        from src.graph.client import LocalGraphClient
        client = LocalGraphClient(self.config.graph_load_dir)
        result = self.retriever.retrieve(
            txn_id=self.sample_txn_id,
            card_id=self.sample_card_id
        )
        for item in result.evidence_items:
            if item.source == "graph":
                for eid in item.entity_ids:
                    if eid and eid.startswith("T") or (eid and eid.isdigit()):
                        # Check transaction ID exists if it looks like one
                        if eid.isdigit():
                            self.assertIn(eid, client.tx_by_id,
                                          f"Fabricated transaction ID {eid} in evidence")

    def test_similar_case_ids_are_strings(self):
        result = self.retriever.retrieve(
            txn_id=self.sample_txn_id,
            card_id=self.sample_card_id
        )
        case_ids = self.retriever.similar_case_ids(result)
        for cid in case_ids:
            self.assertIsInstance(cid, str)
            self.assertGreater(len(cid), 0)

    def test_retrieve_vector_only(self):
        results = self.retriever.retrieve_vector_only(
            query_text="account takeover credentials stolen",
            n_cases=3, n_patterns=2, n_regulatory=2, n_rules=3
        )
        self.assertIn("similar_cases", results)
        self.assertIn("patterns", results)
        self.assertIn("regulatory", results)
        self.assertIn("policy_rules", results)
        self.assertIsInstance(results["similar_cases"], list)

    def test_retrieval_txn_id_in_result(self):
        result = self.retriever.retrieve(
            txn_id=self.sample_txn_id,
            card_id=self.sample_card_id
        )
        self.assertEqual(result.txn_id, self.sample_txn_id)
        self.assertEqual(result.card_id, self.sample_card_id)

    def test_errors_list_is_populated_for_invalid_inputs(self):
        """Invalid txn/card IDs should produce errors, not exceptions."""
        result = self.retriever.retrieve(
            txn_id="INVALID_TXN_XYZ",
            card_id="INVALID_CARD_XYZ"
        )
        self.assertIsInstance(result.errors, list)
        # Should have errors but not raise exceptions
        self.assertGreater(len(result.errors), 0)


if __name__ == "__main__":
    unittest.main()
