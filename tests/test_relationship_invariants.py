import unittest
import pandas as pd
from pathlib import Path
from src.data.config import DataPipelineConfig

class TestRelationshipInvariants(unittest.TestCase):
    def setUp(self):
        self.config = DataPipelineConfig()
        self.vertices_dir = self.config.vertices_dir
        self.edges_dir = self.config.edges_dir

    def test_all_nine_edge_files_exist(self):
        expected_edges = [
            "OWNS.csv", "MADE.csv", "FROM_DEVICE.csv", "PURCHASER_EMAIL.csv",
            "BILLED_IN.csv", "NEXT.csv", "INVOLVES.csv", "ON_CARD.csv", "CONNECTED_TO.csv"
        ]
        for edge_file in expected_edges:
            path = self.edges_dir / edge_file
            self.assertTrue(path.exists(), f"Edge file missing: {edge_file}")

    def test_owns_edge_invariants(self):
        df = pd.read_csv(self.edges_dir / "OWNS.csv")
        self.assertGreater(len(df), 10000, "OWNS edge count unexpectedly small")
        # Check uniqueness of (from_id, to_id)
        dups = df.duplicated(subset=["from_id", "to_id"]).sum()
        self.assertEqual(dups, 0, "Duplicate Customer-Card OWNS edges found")

    def test_on_card_edge_invariants(self):
        df = pd.read_csv(self.edges_dir / "ON_CARD.csv")
        self.assertEqual(len(df), 5565, "ON_CARD edge count must match exact closed case count of 5,565")
        dups = df.duplicated(subset=["from_id", "to_id"]).sum()
        self.assertEqual(dups, 0, "Duplicate ClosedCase-Card ON_CARD edges found")

    def test_connected_to_edge_invariants(self):
        df = pd.read_csv(self.edges_dir / "CONNECTED_TO.csv")
        self.assertEqual(len(df), 92, "CONNECTED_TO edge count must match expected multi-card ring count of 92")

    def test_next_edge_invariants(self):
        df = pd.read_csv(self.edges_dir / "NEXT.csv")
        self.assertGreater(len(df), 500000, "NEXT edge count unexpectedly small")
        dups = df.duplicated(subset=["from_id", "to_id"]).sum()
        self.assertEqual(dups, 0, "Duplicate NEXT transaction transition edges found")

    def test_made_edge_invariants(self):
        df = pd.read_csv(self.edges_dir / "MADE.csv")
        self.assertEqual(len(df), 590742, "MADE edge count must equal total transactions (590,742)")

if __name__ == "__main__":
    unittest.main()
