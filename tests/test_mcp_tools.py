import unittest
from src.tools.mcp_server import (
    TigerGraphMCPServer,
    get_transaction_details,
    get_card_history,
    get_connected_cards_and_customers,
    find_shared_devices,
    get_transaction_neighborhood,
    get_connected_transactions,
    get_historical_closed_cases,
    detect_card_testing_pattern,
    detect_out_of_region_pattern,
    write_case_to_graph
)
from src.data.config import DataPipelineConfig
from src.data.loaders import DataLoader

class TestMCPTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = DataPipelineConfig()
        cls.loader = DataLoader(cls.config)
        cls.case_pack_df = cls.loader.load_case_pack()
        cls.server = TigerGraphMCPServer()

        # Pick first benchmark case for tests
        row0 = cls.case_pack_df.iloc[0]
        cls.sample_txn_id = str(row0["flagged_txn_id"])
        cls.sample_card_id = str(row0["card_id"])
        cls.sample_cust_id = str(row0["customer_id"])

    # Tool 1: get_transaction_details
    def test_get_transaction_details_success(self):
        res = get_transaction_details(self.sample_txn_id)
        self.assertEqual(res["status"], "success")
        self.assertIsNotNone(res["data"])
        self.assertEqual(str(res["data"]["card_id"]), self.sample_card_id)
        self.assertEqual(res["execution_mode"], "offline_local")

    def test_get_transaction_details_not_found(self):
        res = get_transaction_details("INVALID_TXN_99999999")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error_code"], "NOT_FOUND")

    def test_get_transaction_details_invalid_input(self):
        res = get_transaction_details("")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error_code"], "INVALID_INPUT")

    # Tool 2: get_card_history
    def test_get_card_history_success(self):
        res = get_card_history(self.sample_card_id, limit=10)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["card_id"], self.sample_card_id)
        self.assertGreater(res["data"]["total_transactions"], 0)
        self.assertLessEqual(len(res["data"]["transactions"]), 10)

    def test_get_card_history_invalid_limit(self):
        res = get_card_history(self.sample_card_id, limit=-5)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error_code"], "INVALID_INPUT")

    def test_get_card_history_not_found(self):
        res = get_card_history("NONEXISTENT-CARD-X999")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error_code"], "NOT_FOUND")

    # Tool 3: get_connected_cards_and_customers
    def test_get_connected_cards_and_customers_success(self):
        res = get_connected_cards_and_customers(self.sample_card_id)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["card_id"], self.sample_card_id)
        self.assertIn("same_customer_cards", res["data"])
        self.assertIn("shared_device_cards", res["data"])

    def test_get_connected_cards_and_customers_not_found(self):
        res = get_connected_cards_and_customers("NONEXISTENT-CARD-X999")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error_code"], "NOT_FOUND")

    # Tool 4: find_shared_devices
    def test_find_shared_devices_success(self):
        res = find_shared_devices(self.sample_card_id)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["card_id"], self.sample_card_id)
        self.assertIn("device_profiles", res["data"])

    def test_find_shared_devices_not_found(self):
        res = find_shared_devices("NONEXISTENT-CARD-X999")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error_code"], "NOT_FOUND")

    # Tool 5: get_transaction_neighborhood
    def test_get_transaction_neighborhood_success(self):
        res = get_transaction_neighborhood(self.sample_txn_id, depth=2)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["center_transaction_id"], self.sample_txn_id)
        self.assertGreater(res["data"]["node_count"], 0)

    def test_get_transaction_neighborhood_invalid_depth(self):
        res = get_transaction_neighborhood(self.sample_txn_id, depth=5)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error_code"], "INVALID_INPUT")

    # Tool 6: get_connected_transactions
    def test_get_connected_transactions_success(self):
        res = get_connected_transactions(self.sample_card_id)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["card_id"], self.sample_card_id)
        self.assertIn("sequence", res["data"])

    # Tool 7: get_historical_closed_cases
    def test_get_historical_closed_cases_success(self):
        res = get_historical_closed_cases(self.sample_card_id, limit=5)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["card_id"], self.sample_card_id)
        self.assertIn("cases", res["data"])

    # Tool 8: detect_card_testing_pattern
    def test_detect_card_testing_pattern_success(self):
        res = detect_card_testing_pattern(self.sample_card_id)
        self.assertEqual(res["status"], "success")
        self.assertIn("detected", res["data"])

    # Tool 9: detect_out_of_region_pattern
    def test_detect_out_of_region_pattern_success(self):
        res = detect_out_of_region_pattern(self.sample_card_id)
        self.assertEqual(res["status"], "success")
        self.assertIn("detected", res["data"])

    # Tool 10: write_case_to_graph
    def test_write_case_to_graph_success(self):
        res = write_case_to_graph(
            case_id="TEST-CASE-9999",
            customer_id=self.sample_cust_id,
            card_id=self.sample_card_id,
            outcome="confirmed_fraud",
            pattern="card_testing",
            exposure_usd=150.0,
            txn_ids=[self.sample_txn_id],
            actions_taken=["BLOCK_CARD", "CREATE_CASE"],
            report_filed=True,
            analyst_notes="Test offline write"
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["data"]["written"])
        self.assertEqual(res["data"]["mode"], "offline_simulated")
        self.assertEqual(res["data"]["graph_case_id"], "TEST-CASE-9999")

    def test_write_case_to_graph_invalid_outcome(self):
        res = write_case_to_graph(
            case_id="TEST-CASE-9999",
            customer_id=self.sample_cust_id,
            card_id=self.sample_card_id,
            outcome="INVALID_OUTCOME_STRING",
            pattern="card_testing",
            exposure_usd=150.0,
            txn_ids=[self.sample_txn_id]
        )
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error_code"], "INVALID_INPUT")

    # Offline/Live state check
    def test_execution_mode_is_offline_by_default(self):
        self.assertFalse(self.server.engine.is_live_available)


if __name__ == "__main__":
    unittest.main()
