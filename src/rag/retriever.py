"""
Hybrid GraphRAG Retriever — FraudGraph AI Phase 5C
===================================================
Combines graph traversal evidence (Phase 4 MCP tools) with vector retrieval
(Phase 5B vector store) to produce structured, provenanced evidence for each
investigation.

Every evidence item carries:
  - source : "graph" | "document" | "customer" | "external"
  - ref    : query/tool name or document ID
  - claim  : human-readable evidence claim
  - entity_ids : list of IDs the claim rests on

This matches the exact schema required in the answer file:
  evidence[].claim, evidence[].source, evidence[].ref, evidence[].entity_ids
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.tools.mcp_server import TigerGraphMCPServer
from src.rag.vector_store import FraudVectorStore, SearchResult

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Evidence item — exact schema from dataset/HHGOA_IEEE/README.md Answer Format
# ---------------------------------------------------------------------------

@dataclass
class EvidenceItem:
    claim: str
    source: str          # "graph" | "document" | "customer" | "external"
    ref: str             # query name, tool name, or doc_id
    entity_ids: List[str] = field(default_factory=list)
    raw_data: Optional[Any] = None     # original tool/retrieval output for debugging


@dataclass
class HybridRetrievalResult:
    """Structured evidence bundle returned to the investigation agent."""
    txn_id: Optional[str]
    card_id: Optional[str]
    customer_id: Optional[str]

    # Graph evidence
    transaction_details: Optional[Dict[str, Any]] = None
    card_history_summary: Optional[Dict[str, Any]] = None
    connected_entities: Optional[Dict[str, Any]] = None
    shared_devices: Optional[Dict[str, Any]] = None
    connected_transactions_summary: Optional[Dict[str, Any]] = None
    neighborhood: Optional[Dict[str, Any]] = None
    closed_cases: Optional[Dict[str, Any]] = None
    card_testing_result: Optional[Dict[str, Any]] = None
    out_of_region_result: Optional[Dict[str, Any]] = None

    # Vector evidence
    similar_prior_cases: List[SearchResult] = field(default_factory=list)
    relevant_patterns: List[SearchResult] = field(default_factory=list)
    relevant_regulatory_refs: List[SearchResult] = field(default_factory=list)
    relevant_policy_rules: List[SearchResult] = field(default_factory=list)

    # Combined structured evidence (answer-file schema)
    evidence_items: List[EvidenceItem] = field(default_factory=list)

    # Errors encountered (non-fatal)
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class HybridGraphRAGRetriever:
    """
    Hybrid retriever combining Phase 4 graph tools with Phase 5B vector store.

    Parameters
    ----------
    mcp_server  : TigerGraphMCPServer (Phase 4)
    vector_store: FraudVectorStore    (Phase 5B)
    """

    def __init__(
        self,
        mcp_server: Optional[TigerGraphMCPServer] = None,
        vector_store: Optional[FraudVectorStore] = None,
        n_similar_cases: int = 5,
        n_patterns: int = 3,
        n_regulatory: int = 3,
        n_policy_rules: int = 5
    ):
        self.mcp = mcp_server or TigerGraphMCPServer()
        self.vs = vector_store or FraudVectorStore()
        self.n_similar_cases = n_similar_cases
        self.n_patterns = n_patterns
        self.n_regulatory = n_regulatory
        self.n_policy_rules = n_policy_rules

    # ------------------------------------------------------------------
    # Primary retrieval entry point
    # ------------------------------------------------------------------

    def retrieve(
        self,
        txn_id: str,
        card_id: str,
        customer_id: Optional[str] = None,
        query_hint: str = "",
        depth: int = 2
    ) -> HybridRetrievalResult:
        """
        Performs full hybrid retrieval for an investigation.

        Steps
        -----
        1. Fetch transaction details      (tool 1)
        2. Fetch card history             (tool 2)
        3. Get connected cards/customers  (tool 3)
        4. Find shared devices            (tool 4)
        5. Get transaction neighborhood   (tool 5)
        6. Get connected transactions     (tool 6)
        7. Get historical closed cases    (tool 7)
        8. Detect card testing pattern    (tool 8)
        9. Detect out-of-region pattern   (tool 9)
        10. Vector retrieval: similar cases, patterns, regulatory, policy
        11. Assemble provenanced evidence items
        """
        result = HybridRetrievalResult(
            txn_id=txn_id,
            card_id=card_id,
            customer_id=customer_id
        )

        # --- Step 1: Transaction details ---
        tx_res = self.mcp.get_transaction_details(txn_id)
        if tx_res["status"] == "success":
            result.transaction_details = tx_res["data"]
            tx_data = tx_res["data"].get("transaction", {}) or {}
            amt = tx_data.get("TransactionAmt", "?")
            ts  = tx_data.get("ts", "?")
            ch  = tx_data.get("channel", "?")
            risk = tx_data.get("risk_score", "?")
            result.evidence_items.append(EvidenceItem(
                claim=(
                    f"Transaction {txn_id}: amount=${amt}, timestamp={ts}, "
                    f"channel={ch}, risk_score={risk}"
                ),
                source="graph",
                ref=f"tool:get_transaction_details(txn_id={txn_id})",
                entity_ids=[txn_id],
                raw_data=tx_res["data"]
            ))
        else:
            result.errors.append(f"get_transaction_details: {tx_res['message']}")

        # --- Step 2: Card history ---
        hist_res = self.mcp.get_card_history(card_id, limit=50)
        if hist_res["status"] == "success":
            result.card_history_summary = hist_res["data"]
            total = hist_res["data"].get("total_transactions", 0)
            result.evidence_items.append(EvidenceItem(
                claim=f"Card {card_id} has {total} transactions on record.",
                source="graph",
                ref=f"tool:get_card_history(card_id={card_id})",
                entity_ids=[card_id],
                raw_data=hist_res["data"]
            ))
        else:
            result.errors.append(f"get_card_history: {hist_res['message']}")

        # --- Step 3: Connected cards / customers ---
        conn_res = self.mcp.get_connected_cards_and_customers(card_id)
        if conn_res["status"] == "success":
            result.connected_entities = conn_res["data"]
            same_cust_cards = conn_res["data"].get("same_customer_cards", [])
            shared_dev_cards = conn_res["data"].get("shared_device_cards", [])
            if same_cust_cards or shared_dev_cards:
                result.evidence_items.append(EvidenceItem(
                    claim=(
                        f"Card {card_id} shares customer with {len(same_cust_cards)} card(s); "
                        f"shares device profile with {len(shared_dev_cards)} card(s)."
                    ),
                    source="graph",
                    ref=f"tool:get_connected_cards_and_customers(card_id={card_id})",
                    entity_ids=[card_id] + same_cust_cards[:3] + shared_dev_cards[:3],
                    raw_data=conn_res["data"]
                ))
        else:
            result.errors.append(f"get_connected_cards_and_customers: {conn_res['message']}")

        # --- Step 4: Shared devices ---
        dev_res = self.mcp.find_shared_devices(card_id)
        if dev_res["status"] == "success":
            result.shared_devices = dev_res["data"]
            dev_count = dev_res["data"].get("device_profile_count", 0)
            shared_count = dev_res["data"].get("total_shared_cards_count", 0)
            if dev_count > 0:
                result.evidence_items.append(EvidenceItem(
                    claim=(
                        f"Card {card_id} used {dev_count} device profile(s); "
                        f"{shared_count} other card(s) share at least one device profile."
                    ),
                    source="graph",
                    ref=f"tool:find_shared_devices(card_id={card_id})",
                    entity_ids=[card_id] + dev_res["data"].get("shared_cards", [])[:5],
                    raw_data=dev_res["data"]
                ))
        else:
            result.errors.append(f"find_shared_devices: {dev_res['message']}")

        # --- Step 5: Transaction neighborhood ---
        nbr_res = self.mcp.get_transaction_neighborhood(txn_id, depth=depth)
        if nbr_res["status"] == "success":
            result.neighborhood = nbr_res["data"]
            node_count = nbr_res["data"].get("node_count", 0)
            edge_count = nbr_res["data"].get("edge_count", 0)
            result.evidence_items.append(EvidenceItem(
                claim=(
                    f"Transaction {txn_id} has a {depth}-hop neighborhood of "
                    f"{node_count} nodes and {edge_count} edges in the graph."
                ),
                source="graph",
                ref=f"tool:get_transaction_neighborhood(txn_id={txn_id},depth={depth})",
                entity_ids=[txn_id],
                raw_data=nbr_res["data"]
            ))
        else:
            result.errors.append(f"get_transaction_neighborhood: {nbr_res['message']}")

        # --- Step 6: Connected transactions (NEXT chain) ---
        chain_res = self.mcp.get_connected_transactions(card_id)
        if chain_res["status"] == "success":
            result.connected_transactions_summary = chain_res["data"]
            total_txns = chain_res["data"].get("total_transactions", 0)
            result.evidence_items.append(EvidenceItem(
                claim=(
                    f"Card {card_id} NEXT chain contains {total_txns} transactions "
                    f"({chain_res['data'].get('next_edge_count', 0)} NEXT edges)."
                ),
                source="graph",
                ref=f"tool:get_connected_transactions(card_id={card_id})",
                entity_ids=[card_id],
                raw_data=chain_res["data"]
            ))
        else:
            result.errors.append(f"get_connected_transactions: {chain_res['message']}")

        # --- Step 7: Historical closed cases ---
        cases_res = self.mcp.get_historical_closed_cases(card_id, limit=10)
        if cases_res["status"] == "success":
            result.closed_cases = cases_res["data"]
            case_count = cases_res["data"].get("case_count", 0)
            if case_count > 0:
                case_ids = [c.get("case_id") for c in cases_res["data"].get("cases", [])]
                result.evidence_items.append(EvidenceItem(
                    claim=(
                        f"Card {card_id} is connected to {case_count} prior closed "
                        f"investigation case(s): {', '.join(str(c) for c in case_ids[:5])}."
                    ),
                    source="graph",
                    ref=f"tool:get_historical_closed_cases(card_id={card_id})",
                    entity_ids=[card_id] + [str(c) for c in case_ids[:5]],
                    raw_data=cases_res["data"]
                ))
        else:
            result.errors.append(f"get_historical_closed_cases: {cases_res['message']}")

        # --- Step 8: Card testing pattern ---
        ct_res = self.mcp.detect_card_testing_pattern(card_id)
        if ct_res["status"] == "success":
            result.card_testing_result = ct_res["data"]
            if ct_res["data"].get("detected"):
                testing_txns = ct_res["data"].get("testing_txns", [])
                conf = ct_res["data"].get("confidence", 0.0)
                result.evidence_items.append(EvidenceItem(
                    claim=(
                        f"Card testing pattern detected on {card_id} "
                        f"(confidence={conf:.2f}): {len(testing_txns)} small authorization(s) "
                        f"followed by larger purchase. Testing txns: {testing_txns[:5]}."
                    ),
                    source="graph",
                    ref=f"tool:detect_card_testing_pattern(card_id={card_id})",
                    entity_ids=[card_id] + [str(t) for t in testing_txns[:5]],
                    raw_data=ct_res["data"]
                ))
        else:
            result.errors.append(f"detect_card_testing_pattern: {ct_res['message']}")

        # --- Step 9: Out-of-region pattern ---
        oor_res = self.mcp.detect_out_of_region_pattern(card_id)
        if oor_res["status"] == "success":
            result.out_of_region_result = oor_res["data"]
            if oor_res["data"].get("detected"):
                home = oor_res["data"].get("home_region")
                foreign = oor_res["data"].get("foreign_regions", [])
                conf = oor_res["data"].get("confidence", 0.0)
                suspicious = oor_res["data"].get("suspicious_txns", [])
                result.evidence_items.append(EvidenceItem(
                    claim=(
                        f"Out-of-region use detected on {card_id} (confidence={conf:.2f}): "
                        f"home region={home}, foreign regions={foreign}, "
                        f"{len(suspicious)} suspicious in-person transaction(s)."
                    ),
                    source="graph",
                    ref=f"tool:detect_out_of_region_pattern(card_id={card_id})",
                    entity_ids=[card_id] + [t.get("tx_id", "") for t in suspicious[:5]],
                    raw_data=oor_res["data"]
                ))
        else:
            result.errors.append(f"detect_out_of_region_pattern: {oor_res['message']}")

        # --- Step 10: Vector retrieval ---
        self._vector_retrieval(result, txn_id, card_id, query_hint)

        logger.debug(
            f"HybridRetrieval complete for txn={txn_id}, card={card_id}: "
            f"{len(result.evidence_items)} evidence items, {len(result.errors)} errors"
        )
        return result

    # ------------------------------------------------------------------
    # Vector retrieval helper
    # ------------------------------------------------------------------

    def _vector_retrieval(
        self,
        result: HybridRetrievalResult,
        txn_id: str,
        card_id: str,
        query_hint: str
    ) -> None:
        """Runs vector searches and attaches results to the HybridRetrievalResult."""

        # Build a rich query from graph context
        graph_context_parts = []

        if result.card_testing_result and result.card_testing_result.get("detected"):
            graph_context_parts.append("card testing small online authorizations")
        if result.out_of_region_result and result.out_of_region_result.get("detected"):
            graph_context_parts.append("out of region in-person purchase billing region")
        if result.shared_devices and result.shared_devices.get("total_shared_cards_count", 0) > 0:
            graph_context_parts.append("shared device profile multiple cards fraud ring")
        if result.card_history_summary:
            total = result.card_history_summary.get("total_transactions", 0)
            if total > 0:
                graph_context_parts.append(f"card history {total} transactions")

        if query_hint:
            graph_context_parts.append(query_hint)

        query_text = " ".join(graph_context_parts) if graph_context_parts else f"fraud investigation {card_id}"

        # 1. Similar prior cases
        try:
            prior = self.vs.query(query_text, n=self.n_similar_cases, source_types=["closed_case"])
            result.similar_prior_cases = prior
            if prior:
                case_ids = [r.doc.metadata.get("case_id", "") for r in prior]
                result.evidence_items.append(EvidenceItem(
                    claim=(
                        f"Retrieved {len(prior)} similar prior case(s) from history: "
                        f"{', '.join(str(c) for c in case_ids[:5])}."
                    ),
                    source="document",
                    ref="tool:vector_search::closed_cases",
                    entity_ids=[str(c) for c in case_ids[:5]],
                    raw_data=[{"case_id": r.doc.metadata.get("case_id"), "score": r.score, "pattern": r.doc.metadata.get("pattern")} for r in prior]
                ))
        except Exception as e:
            result.errors.append(f"vector_search::closed_cases: {e}")

        # 2. Relevant fraud patterns
        try:
            patterns = self.vs.query(query_text, n=self.n_patterns, source_types=["fraud_pattern"])
            result.relevant_patterns = patterns
            if patterns:
                pattern_names = [r.doc.metadata.get("pattern_id", "") for r in patterns]
                result.evidence_items.append(EvidenceItem(
                    claim=(
                        f"Top matching fraud pattern(s): {', '.join(pattern_names)}."
                    ),
                    source="document",
                    ref="tool:vector_search::fraud_patterns",
                    entity_ids=pattern_names,
                    raw_data=[{"pattern_id": r.doc.metadata.get("pattern_id"), "score": r.score} for r in patterns]
                ))
        except Exception as e:
            result.errors.append(f"vector_search::fraud_patterns: {e}")

        # 3. Regulatory references
        try:
            regulatory = self.vs.query(query_text, n=self.n_regulatory, source_types=["regulatory"])
            result.relevant_regulatory_refs = regulatory
        except Exception as e:
            result.errors.append(f"vector_search::regulatory: {e}")

        # 4. Relevant policy rules
        try:
            policy_rules = self.vs.query(query_text, n=self.n_policy_rules, source_types=["policy_rule"])
            result.relevant_policy_rules = policy_rules
        except Exception as e:
            result.errors.append(f"vector_search::policy_rules: {e}")

    # ------------------------------------------------------------------
    # Convenience: retrieve only vector evidence (no graph calls)
    # ------------------------------------------------------------------

    def retrieve_vector_only(
        self,
        query_text: str,
        n_cases: int = 5,
        n_patterns: int = 3,
        n_regulatory: int = 3,
        n_rules: int = 5
    ) -> Dict[str, List[SearchResult]]:
        """
        Performs vector-only retrieval.  Used for pattern matching and regulatory lookup
        without a specific transaction context.
        """
        return {
            "similar_cases": self.vs.query(query_text, n=n_cases, source_types=["closed_case"]),
            "patterns": self.vs.query(query_text, n=n_patterns, source_types=["fraud_pattern"]),
            "regulatory": self.vs.query(query_text, n=n_regulatory, source_types=["regulatory"]),
            "policy_rules": self.vs.query(query_text, n=n_rules, source_types=["policy_rule"])
        }

    # ------------------------------------------------------------------
    # Format evidence for answer file
    # ------------------------------------------------------------------

    def format_evidence(
        self,
        result: HybridRetrievalResult
    ) -> List[Dict[str, Any]]:
        """
        Returns evidence items in the exact answer-file schema:
          [{"claim": ..., "source": ..., "ref": ..., "entity_ids": [...]}, ...]
        """
        return [
            {
                "claim": e.claim,
                "source": e.source,
                "ref": e.ref,
                "entity_ids": [str(i) for i in e.entity_ids if i]
            }
            for e in result.evidence_items
        ]

    def similar_case_ids(self, result: HybridRetrievalResult) -> List[str]:
        """Returns case IDs of similar prior cases (for answer file similar_prior_cases field)."""
        return [r.doc.metadata.get("case_id", "") for r in result.similar_prior_cases if r.doc.metadata.get("case_id")]
