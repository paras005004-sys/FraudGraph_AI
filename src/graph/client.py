import os
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def _clean_val(val: Any) -> Any:
    """Converts NaN / null values to None and floats to int where appropriate."""
    if pd.isna(val):
        return None
    return val


class LocalGraphClient:
    """In-memory Graph Client for offline testing and fast traversal over data/graph_load/."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/graph_load")
        self.vertices_dir = self.data_dir / "vertices"
        self.edges_dir = self.data_dir / "edges"
        
        self.vertices: Dict[str, pd.DataFrame] = {}
        self.edges: Dict[str, pd.DataFrame] = {}
        
        # Fast lookup indexes
        self.tx_by_id: Dict[str, Dict[str, Any]] = {}
        self.cards_set: Set[str] = set()
        self.customers_set: Set[str] = set()
        
        self.made_tx_to_card: Dict[str, str] = {}
        self.made_card_to_txs: Dict[str, List[str]] = {}
        self.owns_customer_to_cards: Dict[str, List[str]] = {}
        self.owns_card_to_customer: Dict[str, str] = {}
        
        self.from_device_tx_to_dev: Dict[str, str] = {}
        self.from_device_dev_to_txs: Dict[str, List[str]] = {}
        self.purchaser_email_tx_to_domain: Dict[str, str] = {}
        self.billed_in_tx_to_region: Dict[str, str] = {}
        self.next_tx_map: Dict[str, str] = {}
        
        self.closed_cases_list: List[Dict[str, Any]] = []
        self.on_card_case_to_card: Dict[str, str] = {}
        self.on_card_card_to_cases: Dict[str, List[str]] = {}
        self.connected_to_case_to_card: Dict[str, str] = {}
        self.connected_to_card_to_cases: Dict[str, List[str]] = {}
        self.involves_case_to_txs: Dict[str, List[str]] = {}
        
        self._load_data()
        self._build_indexes()
        
    def _load_data(self):
        """Loads vertex and edge CSV files into memory."""
        if not self.vertices_dir.exists() or not self.edges_dir.exists():
            logger.warning(f"Graph load directory not found at {self.data_dir}")
            return
            
        for f in self.vertices_dir.glob("*.csv"):
            v_name = f.stem
            self.vertices[v_name] = pd.read_csv(f, low_memory=False)
            
        for f in self.edges_dir.glob("*.csv"):
            e_name = f.stem
            self.edges[e_name] = pd.read_csv(f, low_memory=False)

    def _build_indexes(self):
        """Builds in-memory dictionary indexes for fast graph traversal."""
        # 1. Transaction vertex index
        if "Transaction" in self.vertices:
            tx_df = self.vertices["Transaction"]
            for row in tx_df.to_dict(orient="records"):
                tid = str(row["TransactionID"])
                cleaned_row = {k: _clean_val(v) for k, v in row.items()}
                self.tx_by_id[tid] = cleaned_row

        # 2. Card vertex set
        if "Card" in self.vertices:
            card_df = self.vertices["Card"]
            if "card_id" in card_df.columns:
                self.cards_set = set(card_df["card_id"].astype(str).values)

        # 3. Customer vertex set
        if "Customer" in self.vertices:
            cust_df = self.vertices["Customer"]
            if "customer_id" in cust_df.columns:
                self.customers_set = set(cust_df["customer_id"].astype(str).values)

        # 4. MADE edges (from: Card, to: Transaction)
        if "MADE" in self.edges:
            made_df = self.edges["MADE"]
            for _, row in made_df.iterrows():
                card_id = str(row["from_id"])
                tx_id = str(row["to_id"])
                self.made_tx_to_card[tx_id] = card_id
                if card_id not in self.made_card_to_txs:
                    self.made_card_to_txs[card_id] = []
                self.made_card_to_txs[card_id].append(tx_id)
                self.cards_set.add(card_id)

        # 5. OWNS edges (from: Customer, to: Card)
        if "OWNS" in self.edges:
            owns_df = self.edges["OWNS"]
            for _, row in owns_df.iterrows():
                cust_id = str(row["from_id"])
                card_id = str(row["to_id"])
                self.owns_card_to_customer[card_id] = cust_id
                if cust_id not in self.owns_customer_to_cards:
                    self.owns_customer_to_cards[cust_id] = []
                self.owns_customer_to_cards[cust_id].append(card_id)
                self.customers_set.add(cust_id)
                self.cards_set.add(card_id)

        # 6. FROM_DEVICE edges (from: Transaction, to: DeviceProfile)
        if "FROM_DEVICE" in self.edges:
            dev_df = self.edges["FROM_DEVICE"]
            for _, row in dev_df.iterrows():
                tx_id = str(row["from_id"])
                dev_id = str(row["to_id"])
                self.from_device_tx_to_dev[tx_id] = dev_id
                if dev_id not in self.from_device_dev_to_txs:
                    self.from_device_dev_to_txs[dev_id] = []
                self.from_device_dev_to_txs[dev_id].append(tx_id)

        # 7. PURCHASER_EMAIL edges (from: Transaction, to: EmailDomain)
        if "PURCHASER_EMAIL" in self.edges:
            email_df = self.edges["PURCHASER_EMAIL"]
            for _, row in email_df.iterrows():
                tx_id = str(row["from_id"])
                domain = str(row["to_id"])
                self.purchaser_email_tx_to_domain[tx_id] = domain

        # 8. BILLED_IN edges (from: Transaction, to: BillingRegion)
        if "BILLED_IN" in self.edges:
            billed_df = self.edges["BILLED_IN"]
            for _, row in billed_df.iterrows():
                tx_id = str(row["from_id"])
                region = str(row["to_id"])
                self.billed_in_tx_to_region[tx_id] = region

        # 9. NEXT edges (from: Transaction, to: Transaction)
        if "NEXT" in self.edges:
            next_df = self.edges["NEXT"]
            for _, row in next_df.iterrows():
                from_tx = str(row["from_id"])
                to_tx = str(row["to_id"])
                self.next_tx_map[from_tx] = to_tx

        # 10. ClosedCase vertex & edges
        if "ClosedCase" in self.vertices:
            case_df = self.vertices["ClosedCase"]
            for row in case_df.to_dict(orient="records"):
                cleaned_row = {k: _clean_val(v) for k, v in row.items()}
                self.closed_cases_list.append(cleaned_row)

        if "ON_CARD" in self.edges:
            on_df = self.edges["ON_CARD"]
            for _, row in on_df.iterrows():
                case_id = str(row["from_id"])
                card_id = str(row["to_id"])
                self.on_card_case_to_card[case_id] = card_id
                if card_id not in self.on_card_card_to_cases:
                    self.on_card_card_to_cases[card_id] = []
                self.on_card_card_to_cases[card_id].append(case_id)

        if "CONNECTED_TO" in self.edges:
            conn_df = self.edges["CONNECTED_TO"]
            for _, row in conn_df.iterrows():
                case_id = str(row["from_id"])
                card_id = str(row["to_id"])
                self.connected_to_case_to_card[case_id] = card_id
                if card_id not in self.connected_to_card_to_cases:
                    self.connected_to_card_to_cases[card_id] = []
                self.connected_to_card_to_cases[card_id].append(case_id)

        if "INVOLVES" in self.edges:
            inv_df = self.edges["INVOLVES"]
            for _, row in inv_df.iterrows():
                case_id = str(row["from_id"])
                tx_id = str(row["to_id"])
                if case_id not in self.involves_case_to_txs:
                    self.involves_case_to_txs[case_id] = []
                self.involves_case_to_txs[case_id].append(tx_id)

    def get_vertex_count(self, vertex_type: str) -> int:
        if vertex_type in self.vertices:
            return len(self.vertices[vertex_type])
        return 0

    def get_edge_count(self, edge_type: str) -> int:
        if edge_type in self.edges:
            return len(self.edges[edge_type])
        return 0

    # ------------------------------------------------------------------------
    # Tool 1: get_transaction_details
    # ------------------------------------------------------------------------
    def get_transaction_details(self, transaction_id: str) -> Dict[str, Any]:
        """Gets transaction details and associated entities."""
        tx_id = str(transaction_id)
        if tx_id not in self.tx_by_id:
            return {}

        tx_info = self.tx_by_id[tx_id]
        card_id = self.made_tx_to_card.get(tx_id)
        customer_id = self.owns_card_to_customer.get(card_id) if card_id else tx_info.get("customer_id")
        device_profile_id = self.from_device_tx_to_dev.get(tx_id)
        email_domain = self.purchaser_email_tx_to_domain.get(tx_id) or tx_info.get("P_emaildomain")
        addr1 = self.billed_in_tx_to_region.get(tx_id) or tx_info.get("addr1")

        return {
            "transaction": tx_info,
            "card_id": card_id,
            "customer_id": customer_id,
            "device_profile_id": device_profile_id,
            "email_domain": email_domain,
            "addr1": str(addr1) if addr1 is not None else None
        }

    # ------------------------------------------------------------------------
    # Tool 2: get_card_history
    # ------------------------------------------------------------------------
    def get_card_history(self, card_id: str, limit: int = 50) -> Dict[str, Any]:
        """Gets transaction history for a card ordered by timestamp."""
        cid = str(card_id)
        if cid not in self.cards_set and cid not in self.made_card_to_txs:
            return {"found": False}

        tx_ids = self.made_card_to_txs.get(cid, [])
        transactions = []
        for tid in tx_ids:
            if tid in self.tx_by_id:
                transactions.append(self.tx_by_id[tid])

        # Sort chronologically by ts
        transactions.sort(key=lambda x: str(x.get("ts", "")))
        customer_id = self.owns_card_to_customer.get(cid)

        return {
            "found": True,
            "card_id": cid,
            "customer_id": customer_id,
            "total_transactions": len(transactions),
            "returned_count": len(transactions[:limit]),
            "transactions": transactions[:limit]
        }

    # ------------------------------------------------------------------------
    # Tool 3: get_connected_cards_and_customers
    # ------------------------------------------------------------------------
    def get_connected_cards_and_customers(self, card_id: str) -> Dict[str, Any]:
        """Gets cards, customers, and cases connected via ownership or shared devices."""
        cid = str(card_id)
        if cid not in self.cards_set and cid not in self.made_card_to_txs:
            return {"found": False}

        customer_id = self.owns_card_to_customer.get(cid)
        same_customer_cards = self.owns_customer_to_cards.get(customer_id, [cid]) if customer_id else [cid]

        # Shared device cards
        tx_ids = self.made_card_to_txs.get(cid, [])
        dev_ids = set()
        for tid in tx_ids:
            dev = self.from_device_tx_to_dev.get(tid)
            if dev:
                dev_ids.add(dev)

        shared_cards_set = set()
        for dev_id in dev_ids:
            connected_txs = self.from_device_dev_to_txs.get(dev_id, [])
            for ctx in connected_txs:
                other_card = self.made_tx_to_card.get(ctx)
                if other_card and other_card != cid:
                    shared_cards_set.add(other_card)

        shared_device_cards = sorted(list(shared_cards_set))

        # Connected customers
        connected_custs_set = set()
        for sc in shared_device_cards:
            cust = self.owns_card_to_customer.get(sc)
            if cust:
                connected_custs_set.add(cust)

        # Connected cases
        connected_cases_set = set()
        for case_id in self.on_card_card_to_cases.get(cid, []):
            connected_cases_set.add(case_id)
        for case_id in self.connected_to_card_to_cases.get(cid, []):
            connected_cases_set.add(case_id)

        return {
            "found": True,
            "card_id": cid,
            "customer_id": customer_id,
            "same_customer_cards": sorted(list(set(same_customer_cards))),
            "shared_device_cards": shared_device_cards,
            "connected_customers": sorted(list(connected_custs_set)),
            "connected_cases": sorted(list(connected_cases_set))
        }

    # ------------------------------------------------------------------------
    # Tool 4: find_shared_devices
    # ------------------------------------------------------------------------
    def find_shared_devices(self, card_id: str) -> Dict[str, Any]:
        """Finds all device profiles used by a card and all other cards sharing them."""
        cid = str(card_id)
        if cid not in self.cards_set and cid not in self.made_card_to_txs:
            return {"found": False}

        tx_ids = self.made_card_to_txs.get(cid, [])
        dev_to_txs: Dict[str, List[str]] = {}
        for tid in tx_ids:
            dev = self.from_device_tx_to_dev.get(tid)
            if dev:
                if dev not in dev_to_txs:
                    dev_to_txs[dev] = []
                dev_to_txs[dev].append(tid)

        device_profiles = []
        all_shared_cards = set()

        for dev_id, card_txs in dev_to_txs.items():
            all_dev_txs = self.from_device_dev_to_txs.get(dev_id, [])
            shared_cards = set()
            for tid in all_dev_txs:
                other_card = self.made_tx_to_card.get(tid)
                if other_card:
                    shared_cards.add(other_card)
                    if other_card != cid:
                        all_shared_cards.add(other_card)

            device_profiles.append({
                "device_profile_id": dev_id,
                "card_transaction_count": len(card_txs),
                "total_device_transaction_count": len(all_dev_txs),
                "shared_cards_count": len(shared_cards),
                "shared_cards": sorted(list(shared_cards))
            })

        return {
            "found": True,
            "card_id": cid,
            "device_profile_count": len(device_profiles),
            "device_profiles": device_profiles,
            "total_shared_cards_count": len(all_shared_cards),
            "shared_cards": sorted(list(all_shared_cards))
        }

    # ------------------------------------------------------------------------
    # Tool 5: get_transaction_neighborhood
    # ------------------------------------------------------------------------
    def get_transaction_neighborhood(self, transaction_id: str, depth: int = 2) -> Dict[str, Any]:
        """Retrieves n-hop subgraph neighborhood around a transaction."""
        tx_id = str(transaction_id)
        if tx_id not in self.tx_by_id:
            return {"found": False}

        nodes = []
        edges = []
        visited_nodes = set()

        # Center node
        center_tx = self.tx_by_id[tx_id]
        nodes.append({"id": tx_id, "type": "Transaction", "label": f"Txn {tx_id}", "data": center_tx})
        visited_nodes.add(("Transaction", tx_id))

        # Hop 1 entities
        card_id = self.made_tx_to_card.get(tx_id)
        if card_id and ("Card", card_id) not in visited_nodes:
            nodes.append({"id": card_id, "type": "Card", "label": f"Card {card_id}"})
            visited_nodes.add(("Card", card_id))
            edges.append({"from": card_id, "to": tx_id, "type": "MADE"})

        dev_id = self.from_device_tx_to_dev.get(tx_id)
        if dev_id and ("DeviceProfile", dev_id) not in visited_nodes:
            nodes.append({"id": dev_id, "type": "DeviceProfile", "label": dev_id[:30] + "..."})
            visited_nodes.add(("DeviceProfile", dev_id))
            edges.append({"from": tx_id, "to": dev_id, "type": "FROM_DEVICE"})

        email = self.purchaser_email_tx_to_domain.get(tx_id)
        if email and ("EmailDomain", email) not in visited_nodes:
            nodes.append({"id": email, "type": "EmailDomain", "label": email})
            visited_nodes.add(("EmailDomain", email))
            edges.append({"from": tx_id, "to": email, "type": "PURCHASER_EMAIL"})

        region = self.billed_in_tx_to_region.get(tx_id)
        if region and ("BillingRegion", region) not in visited_nodes:
            nodes.append({"id": str(region), "type": "BillingRegion", "label": f"Region {region}"})
            visited_nodes.add(("BillingRegion", str(region)))
            edges.append({"from": tx_id, "to": str(region), "type": "BILLED_IN"})

        # Hop 2
        if depth >= 2:
            if card_id:
                cust_id = self.owns_card_to_customer.get(card_id)
                if cust_id and ("Customer", cust_id) not in visited_nodes:
                    nodes.append({"id": cust_id, "type": "Customer", "label": f"Customer {cust_id}"})
                    visited_nodes.add(("Customer", cust_id))
                    edges.append({"from": cust_id, "to": card_id, "type": "OWNS"})

                # Closed cases on card
                cases = self.on_card_card_to_cases.get(card_id, [])
                for cc in cases:
                    if ("ClosedCase", cc) not in visited_nodes:
                        nodes.append({"id": cc, "type": "ClosedCase", "label": f"Case {cc}"})
                        visited_nodes.add(("ClosedCase", cc))
                        edges.append({"from": cc, "to": card_id, "type": "ON_CARD"})

            if dev_id:
                # Other txns on same device (up to 5)
                other_dev_txs = [t for t in self.from_device_dev_to_txs.get(dev_id, []) if t != tx_id][:5]
                for otx in other_dev_txs:
                    if ("Transaction", otx) not in visited_nodes:
                        nodes.append({"id": otx, "type": "Transaction", "label": f"Txn {otx}"})
                        visited_nodes.add(("Transaction", otx))
                        edges.append({"from": otx, "to": dev_id, "type": "FROM_DEVICE"})

        return {
            "found": True,
            "center_transaction_id": tx_id,
            "depth": depth,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges
        }

    # ------------------------------------------------------------------------
    # Tool 6: get_connected_transactions
    # ------------------------------------------------------------------------
    def get_connected_transactions(self, card_id: str) -> Dict[str, Any]:
        """Gets chronological NEXT transaction chain for a card."""
        cid = str(card_id)
        if cid not in self.cards_set and cid not in self.made_card_to_txs:
            return {"found": False}

        tx_ids = self.made_card_to_txs.get(cid, [])
        txs = [self.tx_by_id[t] for t in tx_ids if t in self.tx_by_id]
        txs.sort(key=lambda x: str(x.get("ts", "")))

        next_edges = []
        for i in range(len(txs) - 1):
            curr_id = str(txs[i]["TransactionID"])
            next_id = str(txs[i + 1]["TransactionID"])
            next_edges.append({
                "from_tx": curr_id,
                "to_tx": next_id,
                "type": "NEXT"
            })

        return {
            "found": True,
            "card_id": cid,
            "total_transactions": len(txs),
            "next_edge_count": len(next_edges),
            "sequence": [str(t["TransactionID"]) for t in txs],
            "next_edges": next_edges
        }

    # ------------------------------------------------------------------------
    # Tool 7: get_historical_closed_cases
    # ------------------------------------------------------------------------
    def get_historical_closed_cases(self, card_id: str, limit: int = 10) -> Dict[str, Any]:
        """Gets historical closed cases involving or connected to a card."""
        cid = str(card_id)
        if cid not in self.cards_set and cid not in self.made_card_to_txs:
            return {"found": False}

        matched_case_ids = set()

        # ON_CARD
        for case_id in self.on_card_card_to_cases.get(cid, []):
            matched_case_ids.add(case_id)

        # CONNECTED_TO
        for case_id in self.connected_to_card_to_cases.get(cid, []):
            matched_case_ids.add(case_id)

        # Scan closed cases where card_id appears in card_id or connected_card_ids
        for c in self.closed_cases_list:
            case_id = str(c.get("case_id", ""))
            card_field = str(c.get("card_id", ""))
            conn_field = str(c.get("connected_card_ids", ""))
            if card_field == cid or cid in conn_field:
                matched_case_ids.add(case_id)

        matched_cases = [c for c in self.closed_cases_list if str(c.get("case_id", "")) in matched_case_ids]

        return {
            "found": True,
            "card_id": cid,
            "case_count": len(matched_cases),
            "returned_count": len(matched_cases[:limit]),
            "cases": matched_cases[:limit]
        }

    # ------------------------------------------------------------------------
    # Tool 8: detect_card_testing_pattern
    # ------------------------------------------------------------------------
    def detect_card_testing_pattern(self, card_id: str) -> Dict[str, Any]:
        """Detects card testing pattern: >=3 small online txns (<$5) within 1 hour followed by a larger purchase."""
        cid = str(card_id)
        if cid not in self.cards_set and cid not in self.made_card_to_txs:
            return {"found": False}

        history = self.get_card_history(cid, limit=500)
        txs = history.get("transactions", [])

        # Filter online txns
        online_txs = [t for t in txs if str(t.get("channel", "")).lower() == "online" or str(t.get("ProductCD", "")) != "W"]

        # Parse timestamps and amounts
        parsed_txs = []
        for t in online_txs:
            ts_str = t.get("ts")
            amt = t.get("TransactionAmt")
            tid = str(t.get("TransactionID"))
            if ts_str and amt is not None:
                try:
                    dt = datetime.strptime(str(ts_str), "%Y-%m-%d %H:%M:%S")
                    parsed_txs.append({"tx_id": tid, "dt": dt, "amt": float(amt), "raw": t})
                except ValueError:
                    continue

        parsed_txs.sort(key=lambda x: x["dt"])

        testing_txns = []
        larger_purchase = None
        detected = False
        confidence = 0.0

        for i in range(len(parsed_txs)):
            window_start = parsed_txs[i]["dt"]
            small_txs_in_window = []

            for j in range(i, len(parsed_txs)):
                delta_sec = (parsed_txs[j]["dt"] - window_start).total_seconds()
                if delta_sec <= 3600:  # 1 hour window
                    if parsed_txs[j]["amt"] < 5.0:
                        small_txs_in_window.append(parsed_txs[j])
                else:
                    break

            if len(small_txs_in_window) >= 3:
                # Look for subsequent larger purchase within 2 hours
                window_end_dt = small_txs_in_window[-1]["dt"]
                for k in range(len(parsed_txs)):
                    if parsed_txs[k]["dt"] > window_end_dt and (parsed_txs[k]["dt"] - window_end_dt).total_seconds() <= 7200:
                        if parsed_txs[k]["amt"] > 10.0:
                            larger_purchase = parsed_txs[k]
                            break

                testing_txns = [t["tx_id"] for t in small_txs_in_window]
                detected = True
                confidence = 0.92 if larger_purchase else 0.75
                break

        cleared_over_100 = False
        if larger_purchase and larger_purchase["amt"] > 100.0:
            cleared_over_100 = True

        return {
            "found": True,
            "card_id": cid,
            "detected": detected,
            "confidence": confidence,
            "testing_txns": testing_txns,
            "larger_purchase_txn": larger_purchase["tx_id"] if larger_purchase else None,
            "larger_purchase_amount": larger_purchase["amt"] if larger_purchase else None,
            "cleared_over_100": cleared_over_100,
            "rule": "R5: Card Testing"
        }

    # ------------------------------------------------------------------------
    # Tool 9: detect_out_of_region_pattern
    # ------------------------------------------------------------------------
    def detect_out_of_region_pattern(self, card_id: str) -> Dict[str, Any]:
        """Detects out-of-region pattern: in-person txns in a non-home region."""
        cid = str(card_id)
        if cid not in self.cards_set and cid not in self.made_card_to_txs:
            return {"found": False}

        history = self.get_card_history(cid, limit=500)
        txs = history.get("transactions", [])

        # Find home region (most frequent addr1 across all txns)
        region_counts: Dict[str, int] = {}
        for t in txs:
            addr = t.get("addr1")
            if addr is not None:
                addr_str = str(addr)
                region_counts[addr_str] = region_counts.get(addr_str, 0) + 1

        home_region = max(region_counts, key=region_counts.get) if region_counts else None

        # Filter in_person transactions
        in_person_txs = [t for t in txs if str(t.get("channel", "")).lower() == "in_person" or str(t.get("ProductCD", "")) == "W"]

        suspicious_txns = []
        foreign_regions = set()

        for t in in_person_txs:
            addr = t.get("addr1")
            if addr is not None:
                addr_str = str(addr)
                if home_region and addr_str != home_region:
                    suspicious_txns.append({
                        "tx_id": str(t.get("TransactionID")),
                        "ts": t.get("ts"),
                        "amt": t.get("TransactionAmt"),
                        "addr1": addr_str
                    })
                    foreign_regions.add(addr_str)

        detected = len(suspicious_txns) > 0
        confidence = 0.85 if len(suspicious_txns) >= 2 else (0.65 if detected else 0.0)

        return {
            "found": True,
            "card_id": cid,
            "detected": detected,
            "confidence": confidence,
            "home_region": home_region,
            "foreign_regions": sorted(list(foreign_regions)),
            "suspicious_txns": suspicious_txns,
            "rule": "R2/R3: Out-of-Region Use"
        }

    # ------------------------------------------------------------------------
    # Tool 10: write_case_to_graph
    # ------------------------------------------------------------------------
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
        """Safely writes/upserts a closed case to in-memory graph structures."""
        case_dict = {
            "case_id": case_id,
            "customer_id": customer_id,
            "card_id": card_id,
            "outcome": outcome,
            "pattern": pattern,
            "exposure_usd": float(exposure_usd),
            "txn_ids": "|".join(txn_ids) if isinstance(txn_ids, list) else str(txn_ids),
            "connected_card_ids": "|".join(connected_card_ids) if connected_card_ids else "",
            "actions_taken": "|".join(actions_taken) if actions_taken else "",
            "report_filed": report_filed,
            "analyst_notes": analyst_notes or ""
        }

        self.closed_cases_list.append(case_dict)

        # Update edges
        self.on_card_case_to_card[case_id] = card_id
        if card_id not in self.on_card_card_to_cases:
            self.on_card_card_to_cases[card_id] = []
        self.on_card_card_to_cases[card_id].append(case_id)

        if connected_card_ids:
            for cc in connected_card_ids:
                self.connected_to_case_to_card[case_id] = cc
                if cc not in self.connected_to_card_to_cases:
                    self.connected_to_card_to_cases[cc] = []
                self.connected_to_card_to_cases[cc].append(case_id)

        if txn_ids:
            self.involves_case_to_txs[case_id] = [str(t) for t in txn_ids]

        return {
            "written": True,
            "mode": "offline_simulated",
            "graph_case_id": case_id,
            "message": f"Case '{case_id}' successfully written to offline local graph memory."
        }
