import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.config import DataPipelineConfig
from src.data.loaders import DataLoader
from src.data.relationships import RelationshipExtractor

def main():
    config = DataPipelineConfig()
    loader = DataLoader(config)
    extractor = RelationshipExtractor(loader, config)
    count = extractor.extract_made()
    print(f"Extracted {count} MADE edges into {config.edges_dir / 'MADE.csv'}")

if __name__ == "__main__":
    main()
