import os
import requests
from typing import Dict, Any, List, Optional
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class LiveTigerGraphClient:
    """Live TigerGraph RESTPP client for cloud or docker deployments."""
    
    def __init__(self):
        self.host = os.getenv("TIGERGRAPH_HOST", "").rstrip("/")
        self.port = os.getenv("TIGERGRAPH_PORT", "9000")
        self.graph_name = os.getenv("TIGERGRAPH_GRAPH_NAME", "FraudGraph")
        self.username = os.getenv("TIGERGRAPH_USERNAME", "tigergraph")
        self.password = os.getenv("TIGERGRAPH_PASSWORD", "")
        self.token = os.getenv("TIGERGRAPH_SECRET") or os.getenv("TIGERGRAPH_TOKEN", "")
        
        if self.host and not self.host.startswith("http"):
            self.host = f"http://{self.host}"
            
        self.base_url = f"{self.host}:{self.port}" if self.port and not self.host.count(":") > 1 else self.host

    def is_available(self) -> bool:
        """Checks if live TigerGraph server endpoint is configured and reachable."""
        if not self.host:
            return False
            
        try:
            url = f"{self.base_url}/echo"
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, timeout=2)
            return resp.status_code == 200
        except Exception as e:
            logger.debug(f"Live TigerGraph check failed: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def run_query(self, query_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Runs a compiled GSQL query via TigerGraph RESTPP endpoint."""
        if not self.is_available():
            raise RuntimeError("Live TigerGraph server is not available.")

        url = f"{self.base_url}/query/{self.graph_name}/{query_name}"
        headers = self._get_headers()
        
        auth = None
        if not self.token and self.username and self.password:
            auth = (self.username, self.password)
            
        resp = requests.get(url, headers=headers, params=params, auth=auth, timeout=10)
        if resp.status_code != 200:
            raise RuntimeError(f"GSQL query '{query_name}' failed with status {resp.status_code}: {resp.text}")

        return resp.json()

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
        """Upserts a ClosedCase vertex and edges into live TigerGraph RESTPP endpoint."""
        if not self.is_available():
            raise RuntimeError("Live TigerGraph server is not available.")

        url = f"{self.base_url}/graph/{self.graph_name}"
        headers = self._get_headers()
        auth = (self.username, self.password) if not self.token and self.username else None

        # Vertex payload
        payload = {
            "vertices": {
                "ClosedCase": {
                    case_id: {
                        "outcome": {"value": outcome},
                        "pattern": {"value": pattern},
                        "exposure_usd": {"value": float(exposure_usd)},
                        "actions_taken": {"value": "|".join(actions_taken) if actions_taken else ""},
                        "report_filed": {"value": bool(report_filed)},
                        "analyst_notes": {"value": analyst_notes or ""}
                    }
                }
            },
            "edges": {
                "ClosedCase": {
                    case_id: {
                        "ON_CARD": {
                            "Card": {
                                card_id: {}
                            }
                        }
                    }
                }
            }
        }

        resp = requests.post(url, json=payload, headers=headers, auth=auth, timeout=10)
        if resp.status_code != 200:
            raise RuntimeError(f"Live TigerGraph case write failed: {resp.text}")

        return {
            "written": True,
            "mode": "live_tigergraph",
            "graph_case_id": case_id,
            "response": resp.json()
        }
