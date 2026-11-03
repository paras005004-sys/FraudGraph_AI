from typing import Dict, Any
import json
import pandas as pd
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
from .loaders import DataLoader
from .config import DataPipelineConfig

class DatasetProfiler:
    """Generates aggregate statistics for datasets without dumping raw rows."""
    
    def __init__(self, loader: DataLoader, config: DataPipelineConfig):
        self.loader = loader
        self.config = config
        
    def profile_all(self) -> Dict[str, Any]:
        """Generates comprehensive summary profile of all files."""
        logger.info("Profiling dataset files...")
        
        tx_summary = self._profile_transactions()
        id_summary = self._profile_identity()
        cc_summary = self._profile_closed_cases()
        cp_summary = self._profile_case_pack()
        
        return {
            "transactions": tx_summary,
            "identity": id_summary,
            "closed_cases": cc_summary,
            "case_pack": cp_summary
        }

    def _profile_transactions(self) -> Dict[str, Any]:
        total_rows = 0
        min_risk, max_risk = 1.0, 0.0
        channels = {}
        products = {}
        
        for chunk in self.loader.stream_transactions():
            total_rows += len(chunk)
            if "risk_score" in chunk.columns:
                rs = chunk["risk_score"].dropna()
                if len(rs) > 0:
                    min_risk = min(min_risk, float(rs.min()))
                    max_risk = max(max_risk, float(rs.max()))
                    
            if "channel" in chunk.columns:
                vc = chunk["channel"].value_counts().to_dict()
                for k, v in vc.items():
                    channels[k] = channels.get(k, 0) + int(v)
                    
            if "ProductCD" in chunk.columns:
                vc = chunk["ProductCD"].value_counts().to_dict()
                for k, v in vc.items():
                    products[k] = products.get(k, 0) + int(v)
                    
        return {
            "total_rows": total_rows,
            "total_columns": 397,
            "risk_score_min": min_risk,
            "risk_score_max": max_risk,
            "channel_counts": channels,
            "product_counts": products
        }

    def _profile_identity(self) -> Dict[str, Any]:
        df = self.loader.load_identity()
        dev_types = df["DeviceType"].value_counts().to_dict() if "DeviceType" in df.columns else {}
        top_devices = df["DeviceInfo"].value_counts().head(5).to_dict() if "DeviceInfo" in df.columns else {}
        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "device_types": dev_types,
            "top_device_models": top_devices
        }

    def _profile_closed_cases(self) -> Dict[str, Any]:
        df = self.loader.load_closed_cases()
        outcomes = df["outcome"].value_counts().to_dict()
        patterns = df["pattern"].value_counts().to_dict()
        total_exp = float(df["exposure_usd"].sum())
        return {
            "total_rows": len(df),
            "outcome_counts": outcomes,
            "pattern_counts": patterns,
            "total_exposure_usd": round(total_exp, 2)
        }

    def _profile_case_pack(self) -> Dict[str, Any]:
        df = self.loader.load_case_pack()
        triggers = df["trigger_type"].value_counts().to_dict()
        cases = df["case_id"].tolist()
        return {
            "total_rows": len(df),
            "case_ids": cases,
            "trigger_counts": triggers
        }
