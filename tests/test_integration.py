"""Integration tests for calendar_honey."""

import json
import tempfile
from pathlib import Path
import pytest
from calendar_honey.config import Config
from calendar_honey.ingest import Ingestor


@pytest.fixture
def temp_nest_with_data():
    """Create temporary Nest directory with sample calendar events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nest_path = Path(tmpdir) / "calendar" / "test"
        
        # Create directory structure
        events_dir = nest_path / "history" / "entities" / "calendar" / "primary" / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        
        # Create sample events for multiple days
        events = [
            {
                "envelope": {
                    "source_channel": "calendar",
                    "source_instance": "test",
                    "context_type": "calendar",
                    "context_id": "primary",
                    "context_label": "Primary Calendar",
                    "message_id": f"calendar:primary:event{i}",
                    "remote_id": f"event{i}",
                    "ts": f"2025-11-{20+i:02d}T08:00:00Z",
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
                    "text": f"Test Event {i}",
                    "description": f"Description for event {i}",
                    "location": "Conference Room" if i % 2 == 0 else "",
                    "start_time": f"2025-11-{20+i:02d}T08:00:00Z",
                    "end_time": f"2025-11-{20+i:02d}T09:00:00Z",
                    "all_day": False,
                    "status": "confirmed",
                    "recurring": False
                },
                "raw": {}
            }
            for i in range(1, 6)  # 5 events across different days
        ]
        
        # Write events to files (group by date)
        for event in events:
            date_str = event["envelope"]["ts"].split("T")[0]
            event_file = events_dir / f"{date_str}.jsonl"
            
            # Append to file (multiple events per day)
            with open(event_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        
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
def config(temp_nest_with_data):
    """Create test configuration."""
    from calendar_honey.config import VectorStoreConfig, EmbeddingConfig
    
    tmpdir, _ = temp_nest_with_data
    
    # Use in-memory vector store or temp directory
    honey_path = Path(tmpdir) / "honey" / "calendar" / "test"
    vs_path = honey_path / "vector_store"
    
    return Config(
        data_root=tmpdir,
        instance_id="test",
        channel_type="calendar",
        vector_store=VectorStoreConfig(
            type="chroma",
            path=str(vs_path),
            collection_name="test_calendar_events"
        ),
        embedding=EmbeddingConfig(
            provider="sentence-transformers",
            model="all-MiniLM-L6-v2",
            batch_size=10
        )
    )


@pytest.mark.slow
def test_full_ingestion(config, temp_nest_with_data):
    """Test full ingestion of calendar events."""
    ingestor = Ingestor(config)
    
    # Run full ingestion
    stats = ingestor.ingest_all(force_reindex=True)
    
    assert stats["documents_processed"] == 5
    assert stats["documents_indexed"] == 5
    assert stats["calendars_processed"] == 1
    
    # Verify vector store has documents
    count = ingestor.vector_store.get_count()
    assert count == 5
    
    # Get stats
    stats = ingestor.get_stats()
    assert stats["vector_store"]["document_count"] == 5


@pytest.mark.slow
def test_incremental_ingestion(config, temp_nest_with_data):
    """Test incremental ingestion."""
    ingestor = Ingestor(config)
    
    # First, do full ingestion
    stats = ingestor.ingest_all(force_reindex=True)
    assert stats["documents_indexed"] == 5
    
    # Run incremental (should not add duplicates)
    stats = ingestor.ingest_incremental()
    assert stats["documents_indexed"] == 0  # No new events
    
    # Verify count is still 5
    assert ingestor.vector_store.get_count() == 5


@pytest.mark.slow
def test_query_vector_store(config, temp_nest_with_data):
    """Test querying the vector store."""
    ingestor = Ingestor(config)
    
    # Ingest events
    ingestor.ingest_all(force_reindex=True)
    
    # Generate query embedding
    query_text = "Conference Room"
    query_embedding = ingestor.embedding_service.embed_text(query_text)
    
    # Query vector store
    results = ingestor.vector_store.query(
        query_text=query_text,
        query_embedding=query_embedding,
        n_results=5
    )
    
    # Should find events with location
    assert len(results) > 0
    
    # Check that results have location
    location_results = [
        r for r in results
        if r.get("metadata", {}).get("location", "")
    ]
    assert len(location_results) > 0

