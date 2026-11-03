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

class EntityTransformer:
    """Extracts deterministic graph vertices from validated raw datasets."""
    
    def __init__(self, loader: DataLoader, config: DataPipelineConfig):
        self.loader = loader
        self.config = config
        
    def extract_and_save_all_entities(self) -> Dict[str, int]:
        """Extracts all 7 approved graph entities and writes CSVs to data/graph_load/vertices/."""
        logger.info("Beginning entity extraction for graph loading...")
        
        self.config.vertices_dir.mkdir(parents=True, exist_ok=True)
        
        counts = {}
        
        # 1. Customers
        customers_df = self.extract_customers()
        cust_path = self.config.vertices_dir / "Customer.csv"
        customers_df.to_csv(cust_path, index=False)
        counts["Customer"] = len(customers_df)
        logger.info(f"Saved {len(customers_df)} Customer vertices to {cust_path}")
        
        # 2. Cards
        cards_df = self.extract_cards()
        card_path = self.config.vertices_dir / "Card.csv"
        cards_df.to_csv(card_path, index=False)
        counts["Card"] = len(cards_df)
        logger.info(f"Saved {len(cards_df)} Card vertices to {card_path}")
        
        # 3. Transactions (Chunked)
        tx_count = self.extract_transactions()
        counts["Transaction"] = tx_count
        logger.info(f"Saved {tx_count} Transaction vertices to {self.config.vertices_dir / 'Transaction.csv'}")
        
        # 4. DeviceProfiles
        devices_df = self.extract_device_profiles()
        dev_path = self.config.vertices_dir / "DeviceProfile.csv"
        devices_df.to_csv(dev_path, index=False)
        counts["DeviceProfile"] = len(devices_df)
        logger.info(f"Saved {len(devices_df)} DeviceProfile vertices to {dev_path}")
        
        # 5. EmailDomains
        emails_df = self.extract_email_domains()
        email_path = self.config.vertices_dir / "EmailDomain.csv"
        emails_df.to_csv(email_path, index=False)
        counts["EmailDomain"] = len(emails_df)
        logger.info(f"Saved {len(emails_df)} EmailDomain vertices to {email_path}")
        
        # 6. BillingRegions
        regions_df = self.extract_billing_regions()
        reg_path = self.config.vertices_dir / "BillingRegion.csv"
        regions_df.to_csv(reg_path, index=False)
        counts["BillingRegion"] = len(regions_df)
        logger.info(f"Saved {len(regions_df)} BillingRegion vertices to {reg_path}")
        
        # 7. ClosedCases
        cases_df = self.extract_closed_cases()
        case_path = self.config.vertices_dir / "ClosedCase.csv"
        cases_df.to_csv(case_path, index=False)
        counts["ClosedCase"] = len(cases_df)
        logger.info(f"Saved {len(cases_df)} ClosedCase vertices to {case_path}")
        
        logger.info("Entity extraction completed.")
        return counts

    def extract_customers(self) -> pd.DataFrame:
        """Extracts unique Customer entities."""
        cust_set: Set[str] = set()
        
        for chunk in self.loader.stream_transactions():
            if "customer_id" in chunk.columns:
                cust_set.update(chunk["customer_id"].dropna().astype(str).unique())
                
        closed_df = self.loader.load_closed_cases()
        if "customer_id" in closed_df.columns:
            cust_set.update(closed_df["customer_id"].dropna().astype(str).unique())
            
        case_pack_df = self.loader.load_case_pack()
        if "customer_id" in case_pack_df.columns:
            cust_set.update(case_pack_df["customer_id"].dropna().astype(str).unique())
            
        df = pd.DataFrame({"customer_id": sorted(list(cust_set))})
        return df

    def extract_cards(self) -> pd.DataFrame:
        """Extracts unique Card entities and their metadata."""
        card_dict: Dict[str, Dict[str, Any]] = {}
        
        for chunk in self.loader.stream_transactions():
            if "customer_id" in chunk.columns and "card1" in chunk.columns:
                subset = chunk.dropna(subset=["customer_id", "card1"])
                for _, row in subset.iterrows():
                    cid = str(row["customer_id"])
                    c1 = str(int(row["card1"]))
                    card_id = f"{cid}-K1"  # Standard card naming per dataset
                    
                    if card_id not in card_dict:
                        card_dict[card_id] = {
                            "card_id": card_id,
                            "customer_id": cid,
                            "card1": c1,
                            "card_network": str(row["card4"]) if pd.notnull(row["card4"]) else "",
                            "card_type": str(row["card6"]) if pd.notnull(row["card6"]) else ""
                        }
                        
        closed_df = self.loader.load_closed_cases()
        for _, row in closed_df.iterrows():
            card_id = str(row["card_id"])
            cid = str(row["customer_id"])
            if card_id not in card_dict:
                card_dict[card_id] = {
                    "card_id": card_id,
                    "customer_id": cid,
                    "card1": "",
                    "card_network": "",
                    "card_type": ""
                }
                
        df = pd.DataFrame(list(card_dict.values()))
        return df

    def extract_transactions(self) -> int:
        """Streams transactions and writes Transaction.csv in chunks."""
        tx_path = self.config.vertices_dir / "Transaction.csv"
        first = True
        total = 0
        
        cols_to_keep = [
            "TransactionID", "customer_id", "ts", "channel", "risk_score",
            "TransactionAmt", "ProductCD", "C1", "C2", "C5", "C13", "D1", "D2", "D10", "D15"
        ]
        
        for chunk in self.loader.stream_transactions():
            available_cols = [c for c in cols_to_keep if c in chunk.columns]
            sub_chunk = chunk[available_cols].copy()
            sub_chunk.to_csv(tx_path, mode="w" if first else "a", header=first, index=False)
            first = False
            total += len(sub_chunk)
            
        return total

    def extract_device_profiles(self) -> pd.DataFrame:
        """Extracts unique DeviceProfile entities from identity.csv."""
        id_df = self.loader.load_identity()
        profiles: Dict[str, Dict[str, Any]] = {}
        
        for _, row in id_df.iterrows():
            d_info = str(row["DeviceInfo"]) if pd.notnull(row["DeviceInfo"]) else "UnknownDevice"
            os = str(row["id_30"]) if pd.notnull(row["id_30"]) else "UnknownOS"
            browser = str(row["id_31"]) if pd.notnull(row["id_31"]) else "UnknownBrowser"
            screen = str(row["id_33"]) if pd.notnull(row["id_33"]) else "UnknownScreen"
            
            # Composite profile signature
            device_profile_id = f"{d_info} | {os} | {browser} | {screen}"
            
            if device_profile_id not in profiles:
                profiles[device_profile_id] = {
                    "device_profile_id": device_profile_id,
                    "device_type": str(row["DeviceType"]) if pd.notnull(row["DeviceType"]) else "",
                    "device_info": d_info,
                    "os": os,
                    "browser": browser,
                    "screen": screen,
                    "proxy_status": str(row["id_23"]) if pd.notnull(row["id_23"]) else "",
                    "device_status": str(row["id_15"]) if pd.notnull(row["id_15"]) else ""
                }
                
        df = pd.DataFrame(list(profiles.values()))
        return df

    def extract_email_domains(self) -> pd.DataFrame:
        """Extracts unique EmailDomain entities."""
        domains: Set[str] = set()
        
        for chunk in self.loader.stream_transactions():
            if "P_emaildomain" in chunk.columns:
                domains.update(chunk["P_emaildomain"].dropna().astype(str).unique())
            if "R_emaildomain" in chunk.columns:
                domains.update(chunk["R_emaildomain"].dropna().astype(str).unique())
                
        df = pd.DataFrame({"domain_name": sorted(list(domains))})
        return df

    def extract_billing_regions(self) -> pd.DataFrame:
        """Extracts unique BillingRegion entities (addr1)."""
        addr_dict: Dict[str, float] = {}
        
        for chunk in self.loader.stream_transactions():
            if "addr1" in chunk.columns and "addr2" in chunk.columns:
                valid = chunk.dropna(subset=["addr1"])
                for _, row in valid.iterrows():
                    a1 = str(row["addr1"])
                    a2 = float(row["addr2"]) if pd.notnull(row["addr2"]) else 87.0
                    if a1 not in addr_dict:
                        addr_dict[a1] = a2
                        
        records = [{"addr1": k, "country_code": v} for k, v in addr_dict.items()]
        df = pd.DataFrame(records)
        return df

    def extract_closed_cases(self) -> pd.DataFrame:
        """Extracts ClosedCase entities from closed_cases_history.csv."""
        closed_df = self.loader.load_closed_cases()
        return closed_df.copy()
