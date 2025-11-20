# Calendar Honey

RAG ingestion framework for `calendar_bee` data. This service consumes calendar events from the Nest data directory and indexes them in a vector store for use with RAG (Retrieval-Augmented Generation) systems and MCP (Model Context Protocol) servers.

## Overview

`calendar_honey` is a specialized RAG ingestion service that:

1. **Consumes** calendar events from the `calendar_bee` Nest directory
2. **Transforms** events into RAG-ready documents with rich metadata
3. **Embeds** documents using sentence-transformers or OpenAI embeddings
4. **Indexes** documents in a ChromaDB vector store (compatible with RAG MCP)

The vector store output is optimized for consumption by RAG MCP servers, providing semantic search over your calendar events.

## Features

- **Incremental Indexing**: Only processes new/modified events
- **Calendar-Specific Intelligence**: Handles recurring events, all-day events, attendees, locations
- **Flexible Embeddings**: Supports sentence-transformers (default) or OpenAI embeddings
- **Idempotent**: Safe to re-run, won't duplicate documents
- **ChromaDB Output**: Vector store optimized for MCP consumption
- **Comprehensive Testing**: Test harness with example calendar data

## Installation

```bash
# Clone the repository
git clone https://github.com/runarp/calendar_honey.git
cd calendar_honey

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

## Configuration

Create a `config.yaml` file (see `config.example.yaml`):

```yaml
data_root: ~/Documents/Nest/Calendar
instance_id: personal
channel_type: calendar

vector_store:
  type: chroma
  path: ~/Documents/Nest/Calendar/honey/calendar/personal/vector_store
  collection_name: calendar_events

embedding:
  provider: sentence-transformers
  model: all-MiniLM-L6-v2
  batch_size: 100

transformer:
  include_attendees: true
  include_location: true
  include_description: true
  max_description_length: 2000

indexing:
  mode: incremental
  check_interval_seconds: 300
```

Or use environment variables:

```bash
export DATA_ROOT=~/Documents/Nest/Calendar
export INSTANCE_ID=personal
export VECTOR_STORE_TYPE=chroma
export EMBEDDING_PROVIDER=sentence-transformers
```

## Usage

### Full Ingestion

Index all calendar events from the Nest:

```bash
python -m calendar_honey --mode full --config config.yaml
```

### Incremental Ingestion

Only index new events since last run:

```bash
python -m calendar_honey --mode incremental --config config.yaml
```

### Force Reindex

Force reindexing of all events:

```bash
python -m calendar_honey --mode full --force --config config.yaml
```

### Statistics

View indexing statistics:

```bash
python -m calendar_honey --stats --config config.yaml
```

## Output Format

The service creates a ChromaDB vector store at the configured path. Each document contains:

- **ID**: `calendar:{calendar_id}:{event_id}`
- **Content**: Rich text representation of the event
- **Metadata**: Event details (timestamps, location, attendees, etc.)
- **Embedding**: Vector representation for semantic search

### Example Document

```json
{
  "id": "calendar:primary:event123",
  "content": "Event: Team Meeting\n\nDescription: Weekly team sync...\n\nStarts: 2025-11-20T08:00:00Z\nEnds: 2025-11-20T09:00:00Z\nLocation: Conference Room A\nParticipants: John Doe, Jane Smith\nCalendar: Primary Calendar",
  "metadata": {
    "source_channel": "calendar",
    "calendar_id": "primary",
    "event_id": "event123",
    "start_time": "2025-11-20T08:00:00Z",
    "end_time": "2025-11-20T09:00:00Z",
    "location": "Conference Room A",
    "attendees": ["john@example.com", "jane@example.com"],
    "is_all_day": false,
    "recurring": false,
    "status": "confirmed"
  }
}
```

## RAG MCP Integration

The ChromaDB vector store output is designed to work seamlessly with RAG MCP servers. The MCP server can:

1. **Load the vector store** from the configured path
2. **Query semantically** using embeddings
3. **Filter by metadata** (date ranges, calendars, attendees, etc.)
4. **Retrieve context** for calendar-related queries

Example MCP query:

```python
from chromadb import PersistentClient

client = PersistentClient(path="/path/to/vector_store")
collection = client.get_collection("calendar_events")

# Semantic search
results = collection.query(
    query_texts=["meetings with John next week"],
    n_results=5,
    where={"status": "confirmed"}  # Metadata filtering
)
```

## Architecture

```
Nest (calendar_bee data)
    ↓
Document Loader → Document Transformer → Embedding Service → Vector Store
    ↑                                                    ↓
    └──────────────── Indexing State ───────────────────┘
```

### Components

- **Document Loader**: Reads events from Nest JSONL files
- **Document Transformer**: Converts events to RAG documents with metadata
- **Embedding Service**: Generates vector embeddings (sentence-transformers or OpenAI)
- **Vector Store**: Stores and indexes documents in ChromaDB
- **Indexing State**: Tracks what has been indexed for incremental updates

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run only fast tests (skip integration tests)
pytest -m "not slow"

# Run with coverage
pytest --cov=calendar_honey --cov-report=html
```

### Test Fixtures

The test harness includes example calendar data:

- `fixtures/sample_event.json`: Sample calendar event in normalized format
- Test fixtures create temporary Nest structures with sample events

## Directory Structure

```
calendar_honey/
├── calendar_honey/
│   ├── __init__.py
│   ├── __main__.py              # Entry point
│   ├── config.py                # Configuration
│   ├── storage.py               # Path management
│   ├── document_loader.py       # Load events from Nest
│   ├── document_transformer.py  # Transform to RAG documents
│   ├── embedding_service.py     # Generate embeddings
│   ├── vector_store.py          # ChromaDB interface
│   ├── indexing_state.py        # Track indexing progress
│   └── ingest.py                # Main orchestration
├── tests/
│   ├── test_document_loader.py
│   ├── test_document_transformer.py
│   └── test_integration.py
├── fixtures/
│   └── sample_event.json
├── config.example.yaml
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Data Flow

1. **Read from Nest**: Load calendar events from `$DATA_ROOT/calendar/{instance_id}/history/entities/calendar/*/events/*.jsonl`
2. **Transform**: Convert events to RAG documents with structured content and metadata
3. **Embed**: Generate vector embeddings for semantic search
4. **Index**: Store in ChromaDB vector store
5. **Track**: Update indexing state to enable incremental updates

## Requirements

- Python >= 3.12
- chromadb >= 0.4.0
- sentence-transformers >= 2.2.0 (default) or openai >= 1.0.0 (optional)

## License

[Add license information]

## Related Projects

- [calendar_bee](../calendar_bee): Calendar event listener and mirror service
- [bees](../): Main repository for all bee microservices

## Contributing

[Add contributing guidelines]

