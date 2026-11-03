import sys
from pathlib import Path
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.config import DataPipelineConfig
from src.data.loaders import DataLoader
from src.data.relationships import RelationshipExtractor

def main():
    config = DataPipelineConfig()
    loader = DataLoader(config)
    extractor = RelationshipExtractor(loader, config)
    
    count = extractor.extract_next()
    print(f"Extracted {count} NEXT edges into {config.edges_dir / 'NEXT.csv'}")

if __name__ == "__main__":
    main()
