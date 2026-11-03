import unittest
import pandas as pd
from src.data.config import DataPipelineConfig
from src.data.loaders import DataLoader
from src.data.relationships import RelationshipExtractor

class TestRelationshipExtractor(unittest.TestCase):
    def test_extract_closed_case_edges(self):
        config = DataPipelineConfig()
        loader = DataLoader(config)
        extractor = RelationshipExtractor(loader, config)
        
        counts = extractor.extract_closed_case_edges()
        self.assertIn("INVOLVES", counts)
        self.assertIn("ON_CARD", counts)
        self.assertIn("CONNECTED_TO", counts)
        self.assertEqual(counts["ON_CARD"], 5565)

if __name__ == "__main__":
    unittest.main()
