from typing import Dict, Any, List
import pandas as pd
import numpy as np
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
from .loaders import DataLoader

class DataValidator:
    """Validates raw dataset files according to rules in Step 3."""
    
    def __init__(self, loader: DataLoader):
        self.loader = loader
        
    def validate_all(self) -> Dict[str, Any]:
        """Runs validation across all 4 dataset files."""
        logger.info("Starting comprehensive dataset validation...")
        
        report = {
            "transactions": self.validate_transactions(),
            "identity": self.validate_identity(),
            "closed_cases": self.validate_closed_cases(),
            "case_pack": self.validate_case_pack(),
            "cross_validation": {}
        }
        
        # Cross validation between datasets
        report["cross_validation"] = self._run_cross_validation(
            report["transactions"], report["identity"], report["closed_cases"], report["case_pack"]
        )
        
        logger.info("Dataset validation complete.")
        return report

    def validate_transactions(self) -> Dict[str, Any]:
        """Validates transactions dataset using chunking."""
        logger.info("Validating transactions.csv...")
        
        total_rows = 0
        tx_ids = set()
        duplicate_tx_ids = 0
        null_counts = {}
        risk_score_invalid = 0
        min_ts, max_ts = None, None
        min_risk, max_risk = 1.0, 0.0
        
        required_cols = ["TransactionID", "customer_id", "ts", "channel", "risk_score", "TransactionAmt", "ProductCD", "card1"]
        missing_required_cols = []
        
        for i, chunk in enumerate(self.loader.stream_transactions()):
            if i == 0:
                for col in required_cols:
                    if col not in chunk.columns:
                        missing_required_cols.append(col)
                for col in chunk.columns:
                    null_counts[col] = 0
            
            total_rows += len(chunk)
            
            # Check ID uniqueness
            chunk_ids = chunk["TransactionID"].values
            chunk_unique = set(chunk_ids)
            duplicate_tx_ids += (len(chunk_ids) - len(chunk_unique))
            
            # Global duplicates check
            overlap = tx_ids.intersection(chunk_unique)
            duplicate_tx_ids += len(overlap)
            tx_ids.update(chunk_unique)
            
            # Null counts
            for col in chunk.columns:
                null_counts[col] += chunk[col].isnull().sum()
                
            # Risk score range check
            if "risk_score" in chunk.columns:
                rs = chunk["risk_score"].dropna()
                invalid_rs = ((rs < 0.0) | (rs > 1.0)).sum()
                risk_score_invalid += invalid_rs
                if len(rs) > 0:
                    min_risk = min(min_risk, float(rs.min()))
                    max_risk = max(max_risk, float(rs.max()))
                    
            # Timestamp coverage
            if "ts" in chunk.columns:
                ts_series = chunk["ts"].dropna()
                if len(ts_series) > 0:
                    c_min, c_max = str(ts_series.min()), str(ts_series.max())
                    min_ts = c_min if min_ts is None or c_min < min_ts else min_ts
                    max_ts = c_max if max_ts is None or c_max > max_ts else max_ts

        null_rates = {k: float(v / total_rows) for k, v in null_counts.items()}
        
        return {
            "total_rows": total_rows,
            "unique_transaction_ids": len(tx_ids),
            "duplicate_transaction_ids": duplicate_tx_ids,
            "missing_required_columns": missing_required_cols,
            "risk_score_invalid_count": int(risk_score_invalid),
            "risk_score_range": [min_risk, max_risk],
            "timestamp_range": [min_ts, max_ts],
            "top_null_rates": dict(sorted(null_rates.items(), key=lambda x: x[1], reverse=True)[:15]),
            "transaction_ids_set": tx_ids
        }

    def validate_identity(self) -> Dict[str, Any]:
        """Validates identity.csv dataset."""
        logger.info("Validating identity.csv...")
        df = self.loader.load_identity()
        total_rows = len(df)
        unique_tx_ids = df["TransactionID"].nunique()
        dup_tx_ids = total_rows - unique_tx_ids
        
        null_rates = (df.isnull().sum() / total_rows).to_dict()
        
        return {
            "total_rows": total_rows,
            "unique_transaction_ids": unique_tx_ids,
            "duplicate_transaction_ids": dup_tx_ids,
            "columns_count": len(df.columns),
            "has_device_type": "DeviceType" in df.columns,
            "has_device_info": "DeviceInfo" in df.columns,
            "top_null_rates": dict(sorted(null_rates.items(), key=lambda x: x[1], reverse=True)[:10]),
            "transaction_ids_set": set(df["TransactionID"].values)
        }

    def validate_closed_cases(self) -> Dict[str, Any]:
        """Validates closed_cases_history.csv dataset."""
        logger.info("Validating closed_cases_history.csv...")
        df = self.loader.load_closed_cases()
        total_rows = len(df)
        unique_cases = df["case_id"].nunique()
        
        outcome_counts = df["outcome"].value_counts().to_dict()
        pattern_counts = df["pattern"].value_counts().to_dict()
        
        # Extract referenced transaction IDs
        all_tx_ids = []
        for tx_str in df["txn_ids"].dropna():
            for tid in str(tx_str).split("|"):
                tid_clean = tid.strip()
                if tid_clean.isdigit():
                    all_tx_ids.append(int(tid_clean))
                    
        return {
            "total_rows": total_rows,
            "unique_case_ids": unique_cases,
            "duplicate_case_ids": total_rows - unique_cases,
            "outcome_distribution": outcome_counts,
            "pattern_distribution": pattern_counts,
            "referenced_txn_count": len(all_tx_ids),
            "referenced_txn_ids_set": set(all_tx_ids)
        }

    def validate_case_pack(self) -> Dict[str, Any]:
        """Validates case_pack.csv (20 benchmark cases)."""
        logger.info("Validating case_pack.csv...")
        df = self.loader.load_case_pack()
        total_rows = len(df)
        unique_cases = df["case_id"].nunique()
        
        expected_ids = {f"HHG-{i:03d}" for i in range(1, 21)}
        actual_ids = set(df["case_id"].values)
        missing_ids = list(expected_ids - actual_ids)
        
        trigger_types = df["trigger_type"].value_counts().to_dict()
        flagged_txns = df["flagged_txn_id"].tolist()
        
        return {
            "total_rows": total_rows,
            "unique_case_ids": unique_cases,
            "is_exactly_20_cases": total_rows == 20 and len(actual_ids) == 20,
            "missing_expected_case_ids": missing_ids,
            "trigger_type_distribution": trigger_types,
            "flagged_txn_ids": flagged_txns,
            "flagged_txn_ids_set": set(flagged_txns)
        }

    def _run_cross_validation(self, tx_rep: Dict, id_rep: Dict, cc_rep: Dict, cp_rep: Dict) -> Dict[str, Any]:
        """Validates foreign key relationships between files."""
        tx_set = tx_rep["transaction_ids_set"]
        id_set = id_rep["transaction_ids_set"]
        cc_tx_set = cc_rep["referenced_txn_ids_set"]
        cp_tx_set = cp_rep["flagged_txn_ids_set"]
        
        # Unmatched identity transactions
        unmatched_identity = id_set - tx_set
        
        # Unmatched closed case transactions
        unmatched_cc_tx = cc_tx_set - tx_set
        
        # Unmatched case pack transactions
        unmatched_cp_tx = cp_tx_set - tx_set
        
        return {
            "identity_in_transactions_match_count": len(id_set.intersection(tx_set)),
            "unmatched_identity_transactions_count": len(unmatched_identity),
            "closed_cases_in_transactions_match_count": len(cc_tx_set.intersection(tx_set)),
            "unmatched_closed_cases_transactions_count": len(unmatched_cc_tx),
            "case_pack_in_transactions_match_count": len(cp_tx_set.intersection(tx_set)),
            "unmatched_case_pack_transactions_count": len(unmatched_cp_tx),
            "all_case_pack_txns_valid": len(unmatched_cp_tx) == 0
        }
