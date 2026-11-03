import unittest
import pandas as pd
from pathlib import Path
from src.data.config import DataPipelineConfig
from src.data.loaders import DataLoader

class TestDataLoader(unittest.TestCase):
    def test_loader_config_paths(self):
        config = DataPipelineConfig()
        self.assertEqual(config.transactions_path.name, "transactions.csv")
        self.assertEqual(config.identity_path.name, "identity.csv")
        self.assertEqual(config.closed_cases_path.name, "closed_cases_history.csv")
        self.assertEqual(config.case_pack_path.name, "case_pack.csv")

    def test_load_case_pack(self):
        config = DataPipelineConfig()
        loader = DataLoader(config)
        df = loader.load_case_pack()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 20)
        self.assertIn("case_id", df.columns)
        self.assertIn("flagged_txn_id", df.columns)

    def test_load_closed_cases(self):
        config = DataPipelineConfig()
        loader = DataLoader(config)
        df = loader.load_closed_cases()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 5565)
        self.assertIn("outcome", df.columns)

    def test_stream_transactions_chunk(self):
        config = DataPipelineConfig()
        loader = DataLoader(config)
        chunks = list(loader.stream_transactions(chunk_size=1000))
        self.assertGreater(len(chunks), 0)
        self.assertIsInstance(chunks[0], pd.DataFrame)
        self.assertEqual(len(chunks[0]), 1000)
        self.assertIn("TransactionID", chunks[0].columns)

if __name__ == "__main__":
    unittest.main()
