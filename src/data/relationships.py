from typing import Dict, Any, List, Set, Tuple
import pandas as pd
import numpy as np
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
from .loaders import DataLoader
from .config import DataPipelineConfig

class RelationshipExtractor:
    """Extracts deterministic graph edges from validated raw datasets."""
    
    def __init__(self, loader: DataLoader, config: DataPipelineConfig):
        self.loader = loader
        self.config = config
        
    def extract_and_save_all_relationships(self) -> Dict[str, int]:
        """Extracts all 9 approved graph relationships and writes CSVs to data/graph_load/edges/."""
        logger.info("Beginning relationship extraction for graph loading...")
        
        self.config.edges_dir.mkdir(parents=True, exist_ok=True)
        
        counts = {}
        
        # 1. OWNS (Customer -> Card)
        owns_df = self.extract_owns()
        owns_path = self.config.edges_dir / "OWNS.csv"
        owns_df.to_csv(owns_path, index=False)
        counts["OWNS"] = len(owns_df)
        logger.info(f"Saved {len(owns_df)} OWNS edges to {owns_path}")
        
        # 2. MADE (Card -> Transaction)
        made_count = self.extract_made()
        counts["MADE"] = made_count
        logger.info(f"Saved {made_count} MADE edges to {self.config.edges_dir / 'MADE.csv'}")
        
        # 3. FROM_DEVICE (Transaction -> DeviceProfile)
        from_dev_df = self.extract_from_device()
        from_dev_path = self.config.edges_dir / "FROM_DEVICE.csv"
        from_dev_df.to_csv(from_dev_path, index=False)
        counts["FROM_DEVICE"] = len(from_dev_df)
        logger.info(f"Saved {len(from_dev_df)} FROM_DEVICE edges to {from_dev_path}")
        
        # 4. PURCHASER_EMAIL (Transaction -> EmailDomain)
        p_email_count = self.extract_purchaser_email()
        counts["PURCHASER_EMAIL"] = p_email_count
        logger.info(f"Saved {p_email_count} PURCHASER_EMAIL edges to {self.config.edges_dir / 'PURCHASER_EMAIL.csv'}")
        
        # 5. BILLED_IN (Transaction -> BillingRegion)
        billed_count = self.extract_billed_in()
        counts["BILLED_IN"] = billed_count
        logger.info(f"Saved {billed_count} BILLED_IN edges to {self.config.edges_dir / 'BILLED_IN.csv'}")
        
        # 6. NEXT (Transaction -> Transaction)
        next_count = self.extract_next()
        counts["NEXT"] = next_count
        logger.info(f"Saved {next_count} NEXT edges to {self.config.edges_dir / 'NEXT.csv'}")
        
        # 7. ClosedCase Edges (INVOLVES, ON_CARD, CONNECTED_TO)
        cc_counts = self.extract_closed_case_edges()
        counts.update(cc_counts)
        
        logger.info("Relationship extraction completed.")
        return counts

    def extract_owns(self) -> pd.DataFrame:
        """Extracts OWNS edges (Customer -> Card)."""
        owns_pairs: Set[Tuple[str, str]] = set()
        
        for chunk in self.loader.stream_transactions():
            if "customer_id" in chunk.columns and "card1" in chunk.columns:
                valid = chunk.dropna(subset=["customer_id", "card1"])
                for _, row in valid.iterrows():
                    cid = str(row["customer_id"])
                    card_id = f"{cid}-K1"
                    owns_pairs.add((cid, card_id))
                    
        closed_df = self.loader.load_closed_cases()
        for _, row in closed_df.iterrows():
            cid = str(row["customer_id"])
            card_id = str(row["card_id"])
            owns_pairs.add((cid, card_id))
            
        records = [{"from_id": c, "to_id": k} for c, k in owns_pairs]
        return pd.DataFrame(records)

    def extract_made(self) -> int:
        """Streams transactions and extracts MADE edges (Card -> Transaction)."""
        made_path = self.config.edges_dir / "MADE.csv"
        first = True
        total = 0
        
        # Build explicit transaction -> card_id map from case_pack and closed_cases_history
        explicit_tx_card = {}
        case_pack_df = self.loader.load_case_pack()
        for _, row in case_pack_df.iterrows():
            if pd.notnull(row["flagged_txn_id"]) and pd.notnull(row["card_id"]):
                explicit_tx_card[str(int(row["flagged_txn_id"]))] = str(row["card_id"])
                
        closed_df = self.loader.load_closed_cases()
        for _, row in closed_df.iterrows():
            if pd.notnull(row["card_id"]) and pd.notnull(row["txn_ids"]):
                card_id = str(row["card_id"])
                for tid in str(row["txn_ids"]).split("|"):
                    if tid.strip():
                        explicit_tx_card[tid.strip()] = card_id
        
        for chunk in self.loader.stream_transactions():
            if "customer_id" in chunk.columns and "TransactionID" in chunk.columns:
                valid = chunk.dropna(subset=["customer_id", "TransactionID"]).copy()
                
                # Assign from_id based on explicit card mapping or default -K1
                from_ids = []
                for _, row in valid.iterrows():
                    tx_id = str(int(row["TransactionID"]))
                    cid = str(row["customer_id"])
                    card_id = explicit_tx_card.get(tx_id, f"{cid}-K1")
                    from_ids.append(card_id)
                    
                valid["from_id"] = from_ids
                valid["to_id"] = valid["TransactionID"].astype(str)
                
                sub = valid[["from_id", "to_id"]]
                sub.to_csv(made_path, mode="w" if first else "a", header=first, index=False)
                first = False
                total += len(sub)
                
        return total

    def extract_from_device(self) -> pd.DataFrame:
        """Extracts FROM_DEVICE edges (Transaction -> DeviceProfile)."""
        id_df = self.loader.load_identity()
        records = []
        
        for _, row in id_df.iterrows():
            tx_id = str(int(row["TransactionID"]))
            d_info = str(row["DeviceInfo"]) if pd.notnull(row["DeviceInfo"]) else "UnknownDevice"
            os = str(row["id_30"]) if pd.notnull(row["id_30"]) else "UnknownOS"
            browser = str(row["id_31"]) if pd.notnull(row["id_31"]) else "UnknownBrowser"
            screen = str(row["id_33"]) if pd.notnull(row["id_33"]) else "UnknownScreen"
            
            device_profile_id = f"{d_info} | {os} | {browser} | {screen}"
            
            records.append({
                "from_id": tx_id,
                "to_id": device_profile_id
            })
            
        return pd.DataFrame(records)

    def extract_purchaser_email(self) -> int:
        """Streams transactions and extracts PURCHASER_EMAIL edges (Transaction -> EmailDomain)."""
        path = self.config.edges_dir / "PURCHASER_EMAIL.csv"
        first = True
        total = 0
        
        for chunk in self.loader.stream_transactions():
            if "P_emaildomain" in chunk.columns and "TransactionID" in chunk.columns:
                valid = chunk.dropna(subset=["P_emaildomain", "TransactionID"]).copy()
                valid["from_id"] = valid["TransactionID"].astype(str)
                valid["to_id"] = valid["P_emaildomain"].astype(str)
                
                sub = valid[["from_id", "to_id"]]
                sub.to_csv(path, mode="w" if first else "a", header=first, index=False)
                first = False
                total += len(sub)
                
        return total

    def extract_billed_in(self) -> int:
        """Streams transactions and extracts BILLED_IN edges (Transaction -> BillingRegion)."""
        path = self.config.edges_dir / "BILLED_IN.csv"
        first = True
        total = 0
        
        for chunk in self.loader.stream_transactions():
            if "addr1" in chunk.columns and "TransactionID" in chunk.columns:
                valid = chunk.dropna(subset=["addr1", "TransactionID"]).copy()
                valid["from_id"] = valid["TransactionID"].astype(str)
                valid["to_id"] = valid["addr1"].astype(str)
                
                sub = valid[["from_id", "to_id"]]
                sub.to_csv(path, mode="w" if first else "a", header=first, index=False)
                first = False
                total += len(sub)
                
        return total

    def extract_next(self) -> int:
        """Extracts NEXT edges (Transaction -> Transaction) ordered by timestamp ts per card."""
        card_tx_map: Dict[str, List[Tuple[str, str]]] = {}
        
        for chunk in self.loader.stream_transactions():
            if "customer_id" in chunk.columns and "TransactionID" in chunk.columns and "ts" in chunk.columns:
                valid = chunk.dropna(subset=["customer_id", "TransactionID", "ts"])
                for _, row in valid.iterrows():
                    card_id = f"{row['customer_id']}-K1"
                    tx_id = str(int(row["TransactionID"]))
                    ts = str(row["ts"])
                    if card_id not in card_tx_map:
                        card_tx_map[card_id] = []
                    card_tx_map[card_id].append((ts, tx_id))
                    
        next_records = []
        for card_id, tx_list in card_tx_map.items():
            tx_list.sort(key=lambda x: x[0])
            for i in range(len(tx_list) - 1):
                next_records.append({
                    "from_id": tx_list[i][1],
                    "to_id": tx_list[i+1][1]
                })
                
        df = pd.DataFrame(next_records)
        next_path = self.config.edges_dir / "NEXT.csv"
        df.to_csv(next_path, index=False)
        return len(df)

    def extract_closed_case_edges(self) -> Dict[str, int]:
        """Extracts INVOLVES, ON_CARD, and CONNECTED_TO edges from closed_cases_history.csv."""
        closed_df = self.loader.load_closed_cases()
        
        involves_records = []
        on_card_records = []
        connected_records = []
        
        for _, row in closed_df.iterrows():
            cid = str(row["case_id"])
            card_id = str(row["card_id"])
            
            on_card_records.append({"from_id": cid, "to_id": card_id})
            
            if pd.notnull(row["txn_ids"]):
                for tid in str(row["txn_ids"]).split("|"):
                    if tid.strip():
                        involves_records.append({"from_id": cid, "to_id": tid.strip()})
                        
            if pd.notnull(row["connected_card_ids"]):
                for ccid in str(row["connected_card_ids"]).split("|"):
                    if ccid.strip():
                        connected_records.append({"from_id": cid, "to_id": ccid.strip()})
                        
        inv_df = pd.DataFrame(involves_records)
        inv_path = self.config.edges_dir / "INVOLVES.csv"
        inv_df.to_csv(inv_path, index=False)
        
        onc_df = pd.DataFrame(on_card_records)
        onc_path = self.config.edges_dir / "ON_CARD.csv"
        onc_df.to_csv(onc_path, index=False)
        
        conn_df = pd.DataFrame(connected_records)
        conn_path = self.config.edges_dir / "CONNECTED_TO.csv"
        conn_df.to_csv(conn_path, index=False)
        
        return {
            "INVOLVES": len(inv_df),
            "ON_CARD": len(onc_df),
            "CONNECTED_TO": len(conn_df)
        }
