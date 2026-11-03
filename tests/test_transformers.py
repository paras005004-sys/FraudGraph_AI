import unittest
import pandas as pd
from src.data.config import DataPipelineConfig
from src.data.loaders import DataLoader
from src.data.transformers import EntityTransformer

class TestEntityTransformer(unittest.TestCase):
    def test_extract_closed_cases(self):
        config = DataPipelineConfig()
        loader = DataLoader(config)
        transformer = EntityTransformer(loader, config)
        
        df = transformer.extract_closed_cases()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 5565)
        self.assertIn("case_id", df.columns)

    def test_extract_email_domains(self):
        config = DataPipelineConfig()
        loader = DataLoader(config)
        transformer = EntityTransformer(loader, config)
        
        df = transformer.extract_email_domains()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        self.assertIn("domain_name", df.columns)

if __name__ == "__main__":
    unittest.main()
