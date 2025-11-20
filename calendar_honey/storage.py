"""Directory layout and file system operations for honey."""

from pathlib import Path
from typing import Optional
from .config import Config


class Storage:
    """Manages directory layout for honey data."""
    
    def __init__(self, config: Config):
        self.config = config
        self.honey_path = config.honey_path
        self.nest_path = config.nest_path
        self.state_path = self.honey_path / "state"
        self.cache_path = self.honey_path / "cache"
        self.logs_path = self.honey_path / "logs"
    
    def ensure_directories(self) -> None:
        """Create all required directories."""
        dirs = [
            self.state_path,
            self.cache_path / "embeddings",
            self.logs_path,
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_indexing_state_path(self) -> Path:
        """Path to indexing state file."""
        return self.state_path / "indexing_state.json"
    
    def get_vector_store_metadata_path(self) -> Path:
        """Path to vector store metadata file."""
        return self.state_path / "vector_store_metadata.json"
    
    def get_history_path(self, context_type: str, context_id: str, date_str: str) -> Path:
        """Get path to history file in Nest."""
        return self.nest_path / "history" / "entities" / context_type / context_id / "events" / f"{date_str}.jsonl"
    
    def get_context_path(self, context_type: str, context_id: str) -> Path:
        """Get path to context.json in Nest."""
        return self.nest_path / "history" / "entities" / context_type / context_id / "context.json"
    
    def list_history_files(self, context_type: str = "calendar") -> list[tuple[str, str, Path]]:
        """List all history files in Nest.
        
        Returns list of (context_id, date_str, file_path) tuples.
        """
        history_path = self.nest_path / "history" / "entities" / context_type
        
        if not history_path.exists():
            return []
        
        files = []
        for context_dir in history_path.iterdir():
            if not context_dir.is_dir():
                continue
            
            context_id = context_dir.name
            events_dir = context_dir / "events"
            
            if not events_dir.exists():
                continue
            
            for jsonl_file in events_dir.glob("*.jsonl"):
                date_str = jsonl_file.stem
                files.append((context_id, date_str, jsonl_file))
        
        return files

