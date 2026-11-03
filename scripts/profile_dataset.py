import sys
import json
from pathlib import Path
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.config import DataPipelineConfig
from src.data.loaders import DataLoader
from src.data.profiler import DatasetProfiler

def main():
    logger.info("Starting Dataset Profiling...")
    config = DataPipelineConfig()
    loader = DataLoader(config)
    profiler = DatasetProfiler(loader, config)
    
    summary = profiler.profile_all()
    
    output_path = config.processed_dir / "dataset_profile_summary.json"
    config.processed_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    logger.info(f"Dataset profiling report saved to {output_path}")

if __name__ == "__main__":
    main()
