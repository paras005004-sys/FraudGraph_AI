from typing import Iterator, Optional
import pandas as pd
from pathlib import Path
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
from .config import DataPipelineConfig

class DataLoader:
    """Handles dataset loading with chunking/streaming for large files."""
    
    def __init__(self, config: Optional[DataPipelineConfig] = None):
        self.config = config or DataPipelineConfig()
        
    def stream_transactions(self, chunk_size: Optional[int] = None) -> Iterator[pd.DataFrame]:
        """Streams transactions.csv in chunks."""
        size = chunk_size or self.config.chunk_size
        path = self.config.transactions_path
        logger.info(f"Streaming transactions from {path} in chunks of {size} rows...")
        
        if not path.exists():
            raise FileNotFoundError(f"Transactions dataset file not found at: {path}")
            
        chunk_iter = pd.read_csv(
            path,
            chunksize=size,
            low_memory=False,
            dtype={"TransactionID": int, "customer_id": str, "channel": str}
        )
        
        for i, chunk in enumerate(chunk_iter):
            logger.debug(f"Yielding transactions chunk {i+1} ({len(chunk)} rows)")
            yield chunk

    def load_identity(self) -> pd.DataFrame:
        """Loads identity.csv into memory."""
        path = self.config.identity_path
        logger.info(f"Loading identity dataset from {path}...")
        if not path.exists():
            raise FileNotFoundError(f"Identity file not found at: {path}")
        return pd.read_csv(path, low_memory=False, dtype={"TransactionID": int})

    def load_closed_cases(self) -> pd.DataFrame:
        """Loads closed_cases_history.csv into memory."""
        path = self.config.closed_cases_path
        logger.info(f"Loading closed cases history from {path}...")
        if not path.exists():
            raise FileNotFoundError(f"Closed cases file not found at: {path}")
        return pd.read_csv(path, low_memory=False)

    def load_case_pack(self) -> pd.DataFrame:
        """Loads case_pack.csv into memory."""
        path = self.config.case_pack_path
        logger.info(f"Loading 20 exam cases from {path}...")
        if not path.exists():
            raise FileNotFoundError(f"Case pack file not found at: {path}")
        return pd.read_csv(path, low_memory=False)
