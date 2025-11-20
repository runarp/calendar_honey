"""Tests for document transformer."""

import pytest
from calendar_honey.config import Config
from calendar_honey.document_transformer import DocumentTransformer


@pytest.fixture
def config():
    """Create test configuration."""
    return Config(
        data_root="/tmp/test_honey",
        instance_id="test",
        channel_type="calendar",
    )


@pytest.fixture
def transformer(config):
    """Create document transformer."""
    return DocumentTransformer(config)


@pytest.fixture
def sample_event():
    """Sample calendar event."""
    return {
        "envelope": {
            "source_channel": "calendar",
            "source_instance": "personal",
            "context_type": "calendar",
            "context_id": "primary",
            "context_label": "Primary Calendar",
            "message_id": "calendar:primary:event123",
            "remote_id": "event123",
            "ts": "2025-11-20T08:00:00Z",
            "direction": "inbound",
            "sender": {
                "id": "calendar:organizer@example.com",
                "display_name": "Organizer Name",
                "email": "organizer@example.com",
                "role": "organizer"
            },
            "participants": [
                {
                    "id": "calendar:organizer@example.com",
                    "display_name": "Organizer Name",
                    "email": "organizer@example.com"
                },
                {
                    "id": "calendar:attendee1@example.com",
                    "display_name": "Attendee 1",
                    "email": "attendee1@example.com"
                }
            ],
            "tags": ["calendar", "event"],
            "attachments": []
        },
        "body": {
            "text": "Team Meeting",
            "description": "Weekly team sync",
            "location": "Conference Room A",
            "start_time": "2025-11-20T08:00:00Z",
            "end_time": "2025-11-20T09:00:00Z",
            "all_day": False,
            "status": "confirmed",
            "recurring": False
        },
        "raw": {}
    }


def test_transform_basic_event(transformer, sample_event):
    """Test transforming a basic calendar event."""
    doc = transformer.transform_event(sample_event)
    
    assert doc["id"] == "calendar:primary:event123"
    assert "Event: Team Meeting" in doc["content"]
    assert "Weekly team sync" in doc["content"]
    assert "Conference Room A" in doc["content"]
    
    metadata = doc["metadata"]
    assert metadata["source_channel"] == "calendar"
    assert metadata["calendar_id"] == "primary"
    assert metadata["event_id"] == "event123"
    assert metadata["start_time"] == "2025-11-20T08:00:00Z"
    assert metadata["location"] == "Conference Room A"


def test_transform_all_day_event(transformer):
    """Test transforming an all-day event."""
    event = {
        "envelope": {
            "source_channel": "calendar",
            "source_instance": "personal",
            "context_type": "calendar",
            "context_id": "primary",
            "context_label": "Primary Calendar",
            "message_id": "calendar:primary:event456",
            "remote_id": "event456",
            "ts": "2025-11-20T00:00:00Z",
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
            "text": "All Day Event",
            "description": "",
            "location": "",
            "start_time": "2025-11-20T00:00:00Z",
            "end_time": "2025-11-21T00:00:00Z",
            "all_day": True,
            "status": "confirmed",
            "recurring": False
        },
        "raw": {}
    }
    
    doc = transformer.transform_event(event)
    
    assert "(All Day)" in doc["content"]
    assert doc["metadata"]["is_all_day"] is True


def test_transform_recurring_event(transformer):
    """Test transforming a recurring event."""
    event = {
        "envelope": {
            "source_channel": "calendar",
            "source_instance": "personal",
            "context_type": "calendar",
            "context_id": "primary",
            "context_label": "Primary Calendar",
            "message_id": "calendar:primary:event789",
            "remote_id": "event789",
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
            "text": "Recurring Meeting",
            "description": "",
            "location": "",
            "start_time": "2025-11-20T08:00:00Z",
            "end_time": "2025-11-20T09:00:00Z",
            "all_day": False,
            "status": "confirmed",
            "recurring": True
        },
        "raw": {}
    }
    
    doc = transformer.transform_event(event)
    
    assert "(Recurring Event)" in doc["content"]
    assert doc["metadata"]["recurring"] is True


def test_transform_event_without_location(transformer):
    """Test transforming event without location."""
    event = {
        "envelope": {
            "source_channel": "calendar",
            "source_instance": "personal",
            "context_type": "calendar",
            "context_id": "primary",
            "context_label": "Primary Calendar",
            "message_id": "calendar:primary:event999",
            "remote_id": "event999",
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
            "text": "Virtual Meeting",
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
    
    doc = transformer.transform_event(event)
    
    # Location should not appear in content if empty
    assert "Location:" not in doc["content"]
    assert "location" not in doc["metadata"] or not doc["metadata"].get("location")


def test_batch_transform(transformer, sample_event):
    """Test batch transformation."""
    events = [sample_event]
    
    docs = transformer.batch_transform(events)
    
    assert len(docs) == 1
    assert docs[0]["id"] == "calendar:primary:event123"

