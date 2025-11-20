"""State management for tracking indexing progress."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from .storage import Storage

logger = logging.getLogger(__name__)


class IndexingState:
    """Tracks what has been indexed."""
    
    def __init__(self, storage: Storage):
        self.storage = storage
        self.state_path = storage.get_indexing_state_path()
        self.state: Dict[str, Any] = {}
        self._load_state()
    
    def _load_state(self) -> None:
        """Load state from file."""
        if not self.state_path.exists():
            self.state = {
                "version": "1.0.0",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "calendars": {},
            }
            self._save_state()
            return
        
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                self.state = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load indexing state: {e}. Starting fresh.")
            now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            self.state = {
                "version": "1.0.0",
                "created_at": now,
                "updated_at": now,
                "calendars": {},
            }
    
    def _save_state(self) -> None:
        """Save state to file."""
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        self.storage.ensure_directories()
        
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save indexing state: {e}")
    
    def get_last_indexed_date(self, calendar_id: str) -> Optional[str]:
        """Get the last date that was indexed for a calendar."""
        calendar_state = self.state.get("calendars", {}).get(calendar_id, {})
        return calendar_state.get("last_indexed_date")
    
    def update_last_indexed_date(self, calendar_id: str, date: str) -> None:
        """Update the last indexed date for a calendar."""
        if "calendars" not in self.state:
            self.state["calendars"] = {}
        
        if calendar_id not in self.state["calendars"]:
            now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            self.state["calendars"][calendar_id] = {
                "first_indexed_at": now,
            }
        
        self.state["calendars"][calendar_id]["last_indexed_date"] = date
        self.state["calendars"][calendar_id]["last_indexed_at"] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        self._save_state()
    
    def get_indexed_files(self, calendar_id: str) -> Dict[str, Any]:
        """Get metadata about indexed files for a calendar."""
        calendar_state = self.state.get("calendars", {}).get(calendar_id, {})
        return calendar_state.get("indexed_files", {})
    
    def mark_file_indexed(self, calendar_id: str, file_path: str, event_count: int) -> None:
        """Mark a file as indexed."""
        if "calendars" not in self.state:
            self.state["calendars"] = {}
        
        if calendar_id not in self.state["calendars"]:
            now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            self.state["calendars"][calendar_id] = {
                "first_indexed_at": now,
            }
        
        if "indexed_files" not in self.state["calendars"][calendar_id]:
            self.state["calendars"][calendar_id]["indexed_files"] = {}
        
        self.state["calendars"][calendar_id]["indexed_files"][file_path] = {
            "event_count": event_count,
            "indexed_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        }
        self._save_state()
    
    def is_file_indexed(self, calendar_id: str, file_path: str) -> bool:
        """Check if a file has been indexed."""
        indexed_files = self.get_indexed_files(calendar_id)
        return file_path in indexed_files
    
    def get_calendar_ids(self) -> list[str]:
        """Get list of all calendar IDs that have been indexed."""
        return list(self.state.get("calendars", {}).keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics."""
        calendars = self.state.get("calendars", {})
        
        total_files = 0
        total_events = 0
        
        for calendar_id, calendar_state in calendars.items():
            indexed_files = calendar_state.get("indexed_files", {})
            total_files += len(indexed_files)
            for file_info in indexed_files.values():
                total_events += file_info.get("event_count", 0)
        
        return {
            "total_calendars": len(calendars),
            "total_files_indexed": total_files,
            "total_events_indexed": total_events,
            "calendars": {
                cal_id: {
                    "files_indexed": len(cal_state.get("indexed_files", {})),
                    "last_indexed_date": cal_state.get("last_indexed_date"),
                    "last_indexed_at": cal_state.get("last_indexed_at"),
                }
                for cal_id, cal_state in calendars.items()
            },
        }

