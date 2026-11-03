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
from src.data.validators import DataValidator

def main():
    logger.info("Starting Dataset Validation...")
    config = DataPipelineConfig()
    loader = DataLoader(config)
    validator = DataValidator(loader)
    
    report = validator.validate_all()
    
    # Exclude set objects before saving JSON
    clean_report = {}
    for k, v in report.items():
        if isinstance(v, dict):
            clean_sub = {}
            for sk, sv in v.items():
                if isinstance(sv, set):
                    clean_sub[sk + "_count"] = len(sv)
                else:
                    clean_sub[sk] = sv
            clean_report[k] = clean_sub
        else:
            clean_report[k] = v
            
    output_path = config.processed_dir / "validation_report.json"
    config.processed_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(clean_report, f, indent=2)
        
    logger.info(f"Validation report saved to {output_path}")

if __name__ == "__main__":
    main()
