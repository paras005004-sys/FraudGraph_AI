"""
TigerGraph MCP Server & Tool Registry for FraudGraph AI.

Exposes 10 standardized graph investigation tools that support both live TigerGraph RESTPP API
and offline LocalGraphClient fallback execution paths.
"""

from typing import Dict, Any, List, Optional
from src.graph.queries import GraphQueryEngine

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class TigerGraphMCPServer:
    """MCP Tool Server encapsulating graph investigation tools."""

    def __init__(self, query_engine: Optional[GraphQueryEngine] = None):
        self.engine = query_engine or GraphQueryEngine()

    def _get_exec_mode() -> str:
        return "live_tigergraph" if self.engine.is_live_available else "offline_local"

    # 1. get_transaction_details
    def get_transaction_details(self, txn_id: str) -> Dict[str, Any]:
        """Tool 1: Get transaction vertex details and connected entities."""
        if not txn_id or not str(txn_id).strip():
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "txn_id must be a non-empty string",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        res = self.engine.get_transaction_details(str(txn_id).strip())
        if not res or ("transaction" in res and not res["transaction"]):
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": f"Transaction '{txn_id}' not found in graph",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        return {
            "status": "success",
            "error_code": None,
            "message": f"Successfully retrieved details for transaction '{txn_id}'",
            "data": res,
            "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
        }

    # 2. get_card_history
    def get_card_history(self, card_id: str, limit: int = 50) -> Dict[str, Any]:
        """Tool 2: Get transaction history for a card ordered by timestamp."""
        if not card_id or not str(card_id).strip():
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "card_id must be a non-empty string",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        if limit is None or limit <= 0:
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": f"limit must be a positive integer, got '{limit}'",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        res = self.engine.get_card_history(str(card_id).strip(), limit)
        if isinstance(res, dict) and res.get("found") is False:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": f"Card '{card_id}' not found in graph",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        return {
            "status": "success",
            "error_code": None,
            "message": f"Successfully retrieved transaction history for card '{card_id}'",
            "data": res,
            "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
        }

    # 3. get_connected_cards_and_customers
    def get_connected_cards_and_customers(self, card_id: str) -> Dict[str, Any]:
        """Tool 3: Get cards, customers, and cases connected via ownership or shared devices."""
        if not card_id or not str(card_id).strip():
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "card_id must be a non-empty string",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        res = self.engine.get_connected_cards_and_customers(str(card_id).strip())
        if isinstance(res, dict) and res.get("found") is False:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": f"Card '{card_id}' not found in graph",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        return {
            "status": "success",
            "error_code": None,
            "message": f"Successfully retrieved connected entities for card '{card_id}'",
            "data": res,
            "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
        }

    # 4. find_shared_devices
    def find_shared_devices(self, card_id: str) -> Dict[str, Any]:
        """Tool 4: Find device profiles used by a card and other cards sharing them."""
        if not card_id or not str(card_id).strip():
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "card_id must be a non-empty string",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        res = self.engine.find_shared_devices(str(card_id).strip())
        if isinstance(res, dict) and res.get("found") is False:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": f"Card '{card_id}' not found in graph",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        return {
            "status": "success",
            "error_code": None,
            "message": f"Successfully searched shared devices for card '{card_id}'",
            "data": res,
            "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
        }

    # 5. get_transaction_neighborhood
    def get_transaction_neighborhood(self, txn_id: str, depth: int = 2) -> Dict[str, Any]:
        """Tool 5: Get n-hop graph neighborhood around a transaction."""
        if not txn_id or not str(txn_id).strip():
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "txn_id must be a non-empty string",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        if depth is None or depth < 1 or depth > 3:
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": f"depth must be between 1 and 3, got '{depth}'",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        res = self.engine.get_transaction_neighborhood(str(txn_id).strip(), depth)
        if isinstance(res, dict) and res.get("found") is False:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": f"Transaction '{txn_id}' not found in graph",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        return {
            "status": "success",
            "error_code": None,
            "message": f"Successfully retrieved {depth}-hop neighborhood for transaction '{txn_id}'",
            "data": res,
            "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
        }

    # 6. get_connected_transactions
    def get_connected_transactions(self, card_id: str) -> Dict[str, Any]:
        """Tool 6: Get chronological NEXT transaction chain for a card."""
        if not card_id or not str(card_id).strip():
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "card_id must be a non-empty string",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        res = self.engine.get_connected_transactions(str(card_id).strip())
        if isinstance(res, dict) and res.get("found") is False:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": f"Card '{card_id}' not found in graph",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        return {
            "status": "success",
            "error_code": None,
            "message": f"Successfully retrieved transaction sequence for card '{card_id}'",
            "data": res,
            "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
        }

    # 7. get_historical_closed_cases
    def get_historical_closed_cases(self, card_id: str, limit: int = 10) -> Dict[str, Any]:
        """Tool 7: Get historical closed cases connected to a card."""
        if not card_id or not str(card_id).strip():
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "card_id must be a non-empty string",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        if limit is None or limit <= 0:
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": f"limit must be a positive integer, got '{limit}'",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        res = self.engine.get_historical_closed_cases(str(card_id).strip(), limit)
        if isinstance(res, dict) and res.get("found") is False:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": f"Card '{card_id}' not found in graph",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        return {
            "status": "success",
            "error_code": None,
            "message": f"Successfully retrieved historical closed cases for card '{card_id}'",
            "data": res,
            "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
        }

    # 8. detect_card_testing_pattern
    def detect_card_testing_pattern(self, card_id: str) -> Dict[str, Any]:
        """Tool 8: Detect card testing pattern (R5)."""
        if not card_id or not str(card_id).strip():
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "card_id must be a non-empty string",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        res = self.engine.detect_card_testing_pattern(str(card_id).strip())
        if isinstance(res, dict) and res.get("found") is False:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": f"Card '{card_id}' not found in graph",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        return {
            "status": "success",
            "error_code": None,
            "message": f"Completed card testing pattern check for card '{card_id}'",
            "data": res,
            "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
        }

    # 9. detect_out_of_region_pattern
    def detect_out_of_region_pattern(self, card_id: str) -> Dict[str, Any]:
        """Tool 9: Detect out-of-region use pattern (R2/R3)."""
        if not card_id or not str(card_id).strip():
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "card_id must be a non-empty string",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        res = self.engine.detect_out_of_region_pattern(str(card_id).strip())
        if isinstance(res, dict) and res.get("found") is False:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": f"Card '{card_id}' not found in graph",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        return {
            "status": "success",
            "error_code": None,
            "message": f"Completed out-of-region pattern check for card '{card_id}'",
            "data": res,
            "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
        }

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
        """Tool 10: Writes/upserts a closed case into TigerGraph (or local offline graph memory)."""
        if not case_id or not str(case_id).strip():
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "case_id must be a non-empty string",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        if not card_id or not str(card_id).strip():
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "card_id must be a non-empty string",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        valid_outcomes = {"confirmed_fraud", "cleared", "uncertain"}
        if not outcome or outcome not in valid_outcomes:
            return {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": f"outcome must be one of {valid_outcomes}, got '{outcome}'",
                "data": None,
                "execution_mode": "offline_local" if not self.engine.is_live_available else "live_tigergraph"
            }

        res = self.engine.write_case_to_graph(
            case_id=str(case_id).strip(),
            customer_id=str(customer_id).strip() if customer_id else "",
            card_id=str(card_id).strip(),
            outcome=outcome,
            pattern=pattern or "none",
            exposure_usd=exposure_usd or 0.0,
            txn_ids=txn_ids or [],
            connected_card_ids=connected_card_ids,
            actions_taken=actions_taken,
            report_filed=report_filed,
            analyst_notes=analyst_notes
        )

        return {
            "status": "success",
            "error_code": None,
            "message": f"Successfully processed case write for '{case_id}'",
            "data": res,
            "execution_mode": res.get("mode", "offline_local")
        }


# Convenience module-level instances for direct function invocation
_default_server = TigerGraphMCPServer()

def get_transaction_details(txn_id: str) -> Dict[str, Any]:
    return _default_server.get_transaction_details(txn_id)

def get_card_history(card_id: str, limit: int = 50) -> Dict[str, Any]:
    return _default_server.get_card_history(card_id, limit)

def get_connected_cards_and_customers(card_id: str) -> Dict[str, Any]:
    return _default_server.get_connected_cards_and_customers(card_id)

def find_shared_devices(card_id: str) -> Dict[str, Any]:
    return _default_server.find_shared_devices(card_id)

def get_transaction_neighborhood(txn_id: str, depth: int = 2) -> Dict[str, Any]:
    return _default_server.get_transaction_neighborhood(txn_id, depth)

def get_connected_transactions(card_id: str) -> Dict[str, Any]:
    return _default_server.get_connected_transactions(card_id)

def get_historical_closed_cases(card_id: str, limit: int = 10) -> Dict[str, Any]:
    return _default_server.get_historical_closed_cases(card_id, limit)

def detect_card_testing_pattern(card_id: str) -> Dict[str, Any]:
    return _default_server.detect_card_testing_pattern(card_id)

def detect_out_of_region_pattern(card_id: str) -> Dict[str, Any]:
    return _default_server.detect_out_of_region_pattern(card_id)

def write_case_to_graph(
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
    return _default_server.write_case_to_graph(
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
