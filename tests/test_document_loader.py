"""Tests for document loader."""

import json
import tempfile
from pathlib import Path
import pytest
from calendar_honey.config import Config
from calendar_honey.storage import Storage
from calendar_honey.document_loader import DocumentLoader


@pytest.fixture
def temp_nest():
    """Create temporary Nest directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nest_path = Path(tmpdir) / "calendar" / "test"
        
        # Create directory structure
        events_dir = nest_path / "history" / "entities" / "calendar" / "primary" / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        
        # Create sample event file
        sample_event = {
            "envelope": {
                "source_channel": "calendar",
                "source_instance": "test",
                "context_type": "calendar",
                "context_id": "primary",
                "context_label": "Primary Calendar",
                "message_id": "calendar:primary:event123",
                "remote_id": "event123",
                "ts": "2025-11-20T08:00:00Z",
                "direction": "inbound",
                "sender": {
                    "id": "calendar:organizer@example.com",
                    "display_name": "Organizer",
                    "email": "organizer@example.com"
                },
                "participants": [],
                "tags": [],
                "attachments": []
            },
            "body": {
                "text": "Test Event",
                "description": "",
                "location": "",
                "start_time": "2025-11-20T08:00:00Z",
                "end_time": "2025-11-20T09:00:00Z",
                "all_day": False,
                "status": "confirmed",
                "recurring": False
            },
            "raw": {}
        }
        
        event_file = events_dir / "2025-11-20.jsonl"
        with open(event_file, "w") as f:
            f.write(json.dumps(sample_event) + "\n")
        
        # Create context.json
        context_dir = nest_path / "history" / "entities" / "calendar" / "primary"
        context_file = context_dir / "context.json"
        context_file.write_text(json.dumps({
            "calendar_id": "primary",
            "summary": "Primary Calendar",
            "description": "My primary calendar"
        }))
        
        yield tmpdir, nest_path


@pytest.fixture
def config(temp_nest):
    """Create test configuration."""
    tmpdir, nest_path = temp_nest
    return Config(
        data_root=tmpdir,
        instance_id="test",
        channel_type="calendar",
    )


@pytest.fixture
def storage(config):
    """Create storage instance."""
    return Storage(config)


@pytest.fixture
def loader(storage):
    """Create document loader."""
    return DocumentLoader(storage)


def test_load_events_from_file(loader, temp_nest):
    """Test loading events from a file."""
    _, nest_path = temp_nest
    event_file = nest_path / "history" / "entities" / "calendar" / "primary" / "events" / "2025-11-20.jsonl"
    
    events = list(loader.load_events_from_file(event_file))
    
    assert len(events) == 1
    assert events[0]["envelope"]["message_id"] == "calendar:primary:event123"
    assert events[0]["body"]["text"] == "Test Event"


def test_load_all_events(loader):
    """Test loading all events."""
    events = list(loader.load_all_events())
    
    assert len(events) == 1
    assert events[0]["envelope"]["context_id"] == "primary"


def test_load_events_filtered_by_context(loader):
    """Test loading events filtered by context."""
    events = list(loader.load_all_events(context_id="primary"))
    assert len(events) == 1
    
    events = list(loader.load_all_events(context_id="nonexistent"))
    assert len(events) == 0


def test_get_context_metadata(loader):
    """Test getting context metadata."""
    metadata = loader.get_context_metadata("primary")
    
    assert metadata is not None
    assert metadata["calendar_id"] == "primary"
    assert metadata["summary"] == "Primary Calendar"


def test_list_history_files(storage, temp_nest):
    """Test listing history files."""
    files = storage.list_history_files("calendar")
    
    assert len(files) == 1
    context_id, date_str, file_path = files[0]
    assert context_id == "primary"
    assert date_str == "2025-11-20"
    assert file_path.exists()

