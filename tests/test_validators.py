import unittest
from src.data.config import DataPipelineConfig
from src.data.loaders import DataLoader
from src.data.validators import DataValidator

class TestDataValidator(unittest.TestCase):
    def test_validate_case_pack(self):
        config = DataPipelineConfig()
        loader = DataLoader(config)
        validator = DataValidator(loader)
        res = validator.validate_case_pack()
        
        self.assertTrue(res["is_exactly_20_cases"])
        self.assertEqual(res["unique_case_ids"], 20)
        self.assertEqual(len(res["missing_expected_case_ids"]), 0)

    def test_validate_closed_cases(self):
        config = DataPipelineConfig()
        loader = DataLoader(config)
        validator = DataValidator(loader)
        res = validator.validate_closed_cases()
        
        self.assertEqual(res["total_rows"], 5565)
        self.assertEqual(res["duplicate_case_ids"], 0)
        self.assertIn("confirmed_fraud", res["outcome_distribution"])
        self.assertIn("cleared", res["outcome_distribution"])

if __name__ == "__main__":
    unittest.main()
