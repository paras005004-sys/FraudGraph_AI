import os
from pathlib import Path
from pydantic import BaseModel, Field

class DataPipelineConfig(BaseModel):
    """Configuration settings for the FraudGraph AI data pipeline."""
    
    # Paths
    base_dir: Path = Field(default_factory=lambda: Path(os.getcwd()))
    raw_dataset_dir: Path = Field(default_factory=lambda: Path("dataset/HHGOA_IEEE"))
    processed_dir: Path = Field(default_factory=lambda: Path("data/processed"))
    graph_load_dir: Path = Field(default_factory=lambda: Path("data/graph_load"))
    vertices_dir: Path = Field(default_factory=lambda: Path("data/graph_load/vertices"))
    edges_dir: Path = Field(default_factory=lambda: Path("data/graph_load/edges"))
    docs_dir: Path = Field(default_factory=lambda: Path("docs"))
    
    # Chunking
    chunk_size: int = 100000
    
    # File Names
    transactions_filename: str = "transactions.csv"
    identity_filename: str = "identity.csv"
    closed_cases_filename: str = "closed_cases_history.csv"
    case_pack_filename: str = "case_pack.csv"
    
    def resolve_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return self.base_dir / path

    @property
    def transactions_path(self) -> Path:
        return self.resolve_path(self.raw_dataset_dir / self.transactions_filename)
        
    @property
    def identity_path(self) -> Path:
        return self.resolve_path(self.raw_dataset_dir / self.identity_filename)
        
    @property
    def closed_cases_path(self) -> Path:
        return self.resolve_path(self.raw_dataset_dir / self.closed_cases_filename)
        
    @property
    def case_pack_path(self) -> Path:
        return self.resolve_path(self.raw_dataset_dir / self.case_pack_filename)
