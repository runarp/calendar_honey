"""Main entry point for calendar_honey."""

import argparse
import logging
import sys
from pathlib import Path
from .config import Config
from .ingest import Ingestor

logger = logging.getLogger(__name__)


def setup_logging(log_level: str):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="RAG ingestion framework for calendar_bee data")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config YAML file",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["full", "incremental"],
        default="incremental",
        help="Ingestion mode: full or incremental (default: incremental)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reindexing of already indexed files",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show indexing statistics and exit",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Load config
    config_path = args.config
    if not config_path:
        # Look for config.yaml in current directory
        default_config = Path("config.yaml")
        if default_config.exists():
            config_path = str(default_config)
    
    try:
        config = Config.load(config_path)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return 1
    
    # Initialize ingestor
    try:
        ingestor = Ingestor(config)
    except Exception as e:
        logger.error(f"Failed to initialize ingestor: {e}")
        return 1
    
    # Show stats and exit
    if args.stats:
        stats = ingestor.get_stats()
        import json
        print(json.dumps(stats, indent=2))
        return 0
    
    # Run ingestion
    try:
        if args.mode == "full":
            logger.info("Running full ingestion")
            stats = ingestor.ingest_all(force_reindex=args.force)
        else:
            logger.info("Running incremental ingestion")
            stats = ingestor.ingest_incremental()
        
        logger.info("Ingestion complete")
        logger.info(f"Statistics: {stats}")
        return 0
    except KeyboardInterrupt:
        logger.info("Ingestion interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Error during ingestion: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

