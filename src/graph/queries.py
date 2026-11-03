from typing import Dict, Any, List, Optional
from .client import LocalGraphClient
from .live_client import LiveTigerGraphClient

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class GraphQueryEngine:
    """Unified Graph Query Engine supporting live TigerGraph RESTPP and offline LocalGraphClient fallback."""

    def __init__(self, local_client: Optional[LocalGraphClient] = None, live_client: Optional[LiveTigerGraphClient] = None):
        self.local_client = local_client or LocalGraphClient()
        self.live_client = live_client or LiveTigerGraphClient()

    @property
    def is_live_available(self) -> bool:
        """Returns True if live TigerGraph server is available."""
        return self.live_client.is_available()

    # 1. get_transaction_details
    def get_transaction_details(self, txn_id: str) -> Dict[str, Any]:
        if self.is_live_available:
            try:
                res = self.live_client.run_query("get_transaction_details", {"txn_id": str(txn_id)})
                return {"source": "live_tigergraph", "data": res}
            except Exception as e:
                logger.warning(f"Live query get_transaction_details failed, falling back to local: {e}")

        return self.local_client.get_transaction_details(txn_id)

    # 2. get_card_history
    def get_card_history(self, card_id: str, limit: int = 50) -> Dict[str, Any]:
        if self.is_live_available:
            try:
                res = self.live_client.run_query("get_card_history", {"card_id": str(card_id), "limit": limit})
                return {"source": "live_tigergraph", "data": res}
            except Exception as e:
                logger.warning(f"Live query get_card_history failed, falling back to local: {e}")

        return self.local_client.get_card_history(card_id, limit)

    # 3. get_connected_cards_and_customers
    def get_connected_cards_and_customers(self, card_id: str) -> Dict[str, Any]:
        if self.is_live_available:
            try:
                res = self.live_client.run_query("get_connected_cards_and_customers", {"card_id": str(card_id)})
                return {"source": "live_tigergraph", "data": res}
            except Exception as e:
                logger.warning(f"Live query get_connected_cards_and_customers failed, falling back to local: {e}")

        return self.local_client.get_connected_cards_and_customers(card_id)

    # 4. find_shared_devices
    def find_shared_devices(self, card_id: str) -> Dict[str, Any]:
        if self.is_live_available:
            try:
                res = self.live_client.run_query("find_shared_devices", {"card_id": str(card_id)})
                return {"source": "live_tigergraph", "data": res}
            except Exception as e:
                logger.warning(f"Live query find_shared_devices failed, falling back to local: {e}")

        return self.local_client.find_shared_devices(card_id)

    # 5. get_transaction_neighborhood
    def get_transaction_neighborhood(self, txn_id: str, depth: int = 2) -> Dict[str, Any]:
        if self.is_live_available:
            try:
                res = self.live_client.run_query("get_transaction_neighborhood", {"txn_id": str(txn_id), "max_hops": depth})
                return {"source": "live_tigergraph", "data": res}
            except Exception as e:
                logger.warning(f"Live query get_transaction_neighborhood failed, falling back to local: {e}")

        return self.local_client.get_transaction_neighborhood(txn_id, depth)

    # 6. get_connected_transactions
    def get_connected_transactions(self, card_id: str) -> Dict[str, Any]:
        if self.is_live_available:
            try:
                res = self.live_client.run_query("get_connected_transactions", {"card_id": str(card_id)})
                return {"source": "live_tigergraph", "data": res}
            except Exception as e:
                logger.warning(f"Live query get_connected_transactions failed, falling back to local: {e}")

        return self.local_client.get_connected_transactions(card_id)

    # 7. get_historical_closed_cases
    def get_historical_closed_cases(self, card_id: str, limit: int = 10) -> Dict[str, Any]:
        if self.is_live_available:
            try:
                res = self.live_client.run_query("get_historical_closed_cases", {"target_card_id": str(card_id)})
                return {"source": "live_tigergraph", "data": res}
            except Exception as e:
                logger.warning(f"Live query get_historical_closed_cases failed, falling back to local: {e}")

        return self.local_client.get_historical_closed_cases(card_id, limit)

    # 8. detect_card_testing_pattern
    def detect_card_testing_pattern(self, card_id: str) -> Dict[str, Any]:
        return self.local_client.detect_card_testing_pattern(card_id)

    # 9. detect_out_of_region_pattern
    def detect_out_of_region_pattern(self, card_id: str) -> Dict[str, Any]:
        return self.local_client.detect_out_of_region_pattern(card_id)

    # 10. write_case_to_graph
    def write_case_to_graph(
        self,
        case_id: str,
        customer_id: str,
        card_id: str,
        outcome: str,
        pattern: str,
        exposure_usd: float,
        txn_ids: List[str],
        connected_card_ids: Optional[List[str]] = None,
        actions_taken: Optional[List[str]] = None,
        report_filed: bool = False,
        analyst_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        if self.is_live_available:
            try:
                return self.live_client.write_case_to_graph(
                    case_id=case_id,
                    customer_id=customer_id,
                    card_id=card_id,
                    outcome=outcome,
                    pattern=pattern,
                    exposure_usd=exposure_usd,
                    txn_ids=txn_ids,
                    connected_card_ids=connected_card_ids,
                    actions_taken=actions_taken,
                    report_filed=report_filed,
                    analyst_notes=analyst_notes
                )
            except Exception as e:
                logger.warning(f"Live write_case_to_graph failed, falling back to local: {e}")

        return self.local_client.write_case_to_graph(
            case_id=case_id,
            customer_id=customer_id,
            card_id=card_id,
            outcome=outcome,
            pattern=pattern,
            exposure_usd=exposure_usd,
            txn_ids=txn_ids,
            connected_card_ids=connected_card_ids,
            actions_taken=actions_taken,
            report_filed=report_filed,
            analyst_notes=analyst_notes
        )
