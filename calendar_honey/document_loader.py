"""Load calendar events from Nest data directory."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Iterator, Optional
from .storage import Storage

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Loads calendar events from Nest history files."""
    
    def __init__(self, storage: Storage):
        self.storage = storage
    
    def load_events_from_file(self, file_path: Path) -> Iterator[Dict[str, Any]]:
        """Load all events from a single JSONL file."""
        if not file_path.exists():
            logger.debug(f"File does not exist: {file_path}")
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event = json.loads(line)
                        yield event
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON at {file_path}:{line_num}: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
    
    def load_all_events(
        self,
        context_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Load all events from Nest, optionally filtered by context and date range."""
        history_files = self.storage.list_history_files("calendar")
        
        for ctx_id, date_str, file_path in history_files:
            # Filter by context_id if provided
            if context_id and ctx_id != context_id:
                continue
            
            # Filter by date range if provided
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue
            
            # Load events from this file
            for event in self.load_events_from_file(file_path):
                yield event
    
    def get_context_metadata(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a calendar context."""
        context_path = self.storage.get_context_path("calendar", context_id)
        
        if not context_path.exists():
            return None
        
        try:
            with open(context_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load context metadata from {context_path}: {e}")
            return None
    
    def load_events_since(
        self,
        context_id: str,
        since_date: str,
    ) -> Iterator[Dict[str, Any]]:
        """Load events from a specific context since a given date."""
        return self.load_all_events(context_id=context_id, start_date=since_date)

