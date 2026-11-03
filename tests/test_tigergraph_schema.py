import unittest
import pandas as pd
from pathlib import Path
from src.graph.client import LocalGraphClient
from src.data.config import DataPipelineConfig
from src.data.loaders import DataLoader

class TestTigerGraphSchema(unittest.TestCase):
    def setUp(self):
        self.config = DataPipelineConfig()
        self.client = LocalGraphClient(self.config.graph_load_dir)

    def test_vertex_counts(self):
        expected_vertices = {
            "Transaction": 590742,
            "Card": 13933,
            "Customer": 13553,
            "DeviceProfile": 9706,
            "ClosedCase": 5565,
            "BillingRegion": 332,
            "EmailDomain": 60
        }
        for v_type, expected_count in expected_vertices.items():
            actual = self.client.get_vertex_count(v_type)
            self.assertEqual(actual, expected_count, f"Vertex {v_type} count mismatch: expected {expected_count}, got {actual}")

    def test_edge_counts(self):
        expected_edges = {
            "OWNS": 13933,
            "MADE": 590742,
            "FROM_DEVICE": 144432,
            "PURCHASER_EMAIL": 496262,
            "BILLED_IN": 525003,
            "NEXT": 577189,
            "INVOLVES": 14955,
            "ON_CARD": 5565,
            "CONNECTED_TO": 92
        }
        for e_type, expected_count in expected_edges.items():
            actual = self.client.get_edge_count(e_type)
            self.assertEqual(actual, expected_count, f"Edge {e_type} count mismatch: expected {expected_count}, got {actual}")

    def test_benchmark_case_traversal(self):
        loader = DataLoader(self.config)
        case_pack_df = loader.load_case_pack()
        self.assertEqual(len(case_pack_df), 20)
        
        # Test traversal for all 20 benchmark transactions
        for _, row in case_pack_df.iterrows():
            txn_id = str(row["flagged_txn_id"])
            details = self.client.get_transaction_details(txn_id)
            self.assertIn("transaction", details, f"Transaction {txn_id} not found in graph")
            self.assertIn("card_id", details)
            self.assertEqual(str(details["card_id"]), str(row["card_id"]), f"Card mismatch for txn {txn_id}")

if __name__ == "__main__":
    unittest.main()
