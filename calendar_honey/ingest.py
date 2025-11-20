"""Main ingestion orchestration logic."""

import logging
from typing import List, Dict, Any
from .config import Config
from .storage import Storage
from .document_loader import DocumentLoader
from .document_transformer import DocumentTransformer
from .embedding_service import EmbeddingService
from .vector_store import VectorStore
from .indexing_state import IndexingState

logger = logging.getLogger(__name__)


class Ingestor:
    """Main ingestion orchestrator."""
    
    def __init__(self, config: Config):
        self.config = config
        self.storage = Storage(config)
        self.loader = DocumentLoader(self.storage)
        self.transformer = DocumentTransformer(config)
        self.embedding_service = EmbeddingService(config)
        self.vector_store = VectorStore(config)
        self.indexing_state = IndexingState(self.storage)
        
        # Ensure directories exist
        self.storage.ensure_directories()
    
    def ingest_all(self, force_reindex: bool = False) -> Dict[str, Any]:
        """Ingest all events from Nest."""
        logger.info("Starting full ingestion")
        
        stats = {
            "documents_processed": 0,
            "documents_indexed": 0,
            "calendars_processed": 0,
            "errors": 0,
        }
        
        # Get all history files
        history_files = self.storage.list_history_files("calendar")
        
        # Group by calendar
        calendars = {}
        for context_id, date_str, file_path in history_files:
            if context_id not in calendars:
                calendars[context_id] = []
            calendars[context_id].append((date_str, file_path))
        
        # Process each calendar
        for calendar_id, files in calendars.items():
            logger.info(f"Processing calendar: {calendar_id} ({len(files)} files)")
            
            try:
                calendar_stats = self._ingest_calendar(calendar_id, files, force_reindex)
                stats["documents_processed"] += calendar_stats["documents_processed"]
                stats["documents_indexed"] += calendar_stats["documents_indexed"]
                stats["calendars_processed"] += 1
            except Exception as e:
                logger.error(f"Error processing calendar {calendar_id}: {e}")
                stats["errors"] += 1
        
        logger.info(f"Ingestion complete: {stats}")
        return stats
    
    def _ingest_calendar(
        self,
        calendar_id: str,
        files: List[tuple[str, Any]],
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """Ingest events from a single calendar."""
        stats = {
            "documents_processed": 0,
            "documents_indexed": 0,
        }
        
        # Get context metadata
        context_metadata = self.loader.get_context_metadata(calendar_id)
        
        # Sort files by date
        files.sort(key=lambda x: x[0])
        
        # Process each file
        batch_size = self.config.embedding.batch_size
        batch_events = []
        batch_files = []
        
        for date_str, file_path in files:
            # Check if already indexed (unless force_reindex)
            if not force_reindex:
                if self.indexing_state.is_file_indexed(calendar_id, str(file_path)):
                    logger.debug(f"Skipping already indexed file: {file_path}")
                    continue
            
            # Load events from file
            events = list(self.loader.load_events_from_file(file_path))
            if not events:
                continue
            
            logger.debug(f"Loaded {len(events)} events from {file_path}")
            
            # Transform events
            documents = self.transformer.batch_transform(events, context_metadata)
            
            if not documents:
                continue
            
            # Add to batch
            batch_events.extend(documents)
            batch_files.append((file_path, len(events)))
            
            # Process batch when it reaches batch size
            if len(batch_events) >= batch_size:
                indexed_count = self._process_batch(batch_events, calendar_id, batch_files)
                stats["documents_processed"] += len(batch_events)
                stats["documents_indexed"] += indexed_count
                batch_events = []
                batch_files = []
        
        # Process remaining batch
        if batch_events:
            indexed_count = self._process_batch(batch_events, calendar_id, batch_files)
            stats["documents_processed"] += len(batch_events)
            stats["documents_indexed"] += indexed_count
        
        # Update last indexed date
        if files:
            last_date = files[-1][0]
            self.indexing_state.update_last_indexed_date(calendar_id, last_date)
        
        return stats
    
    def _process_batch(
        self,
        documents: List[Dict[str, Any]],
        calendar_id: str,
        file_info: List[tuple],
    ) -> int:
        """Process a batch of documents: embed and index."""
        if not documents:
            return 0
        
        logger.debug(f"Processing batch of {len(documents)} documents")
        
        # Generate embeddings
        contents = [doc["content"] for doc in documents]
        try:
            embeddings = self.embedding_service.embed_batch(contents)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return 0
        
        # Add to vector store
        try:
            self.vector_store.add_documents(documents, embeddings)
            
            # Mark files as indexed
            for file_path, event_count in file_info:
                self.indexing_state.mark_file_indexed(calendar_id, str(file_path), event_count)
            
            return len(documents)
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            return 0
    
    def ingest_incremental(self) -> Dict[str, Any]:
        """Ingest only new events since last indexing."""
        logger.info("Starting incremental ingestion")
        
        stats = {
            "documents_processed": 0,
            "documents_indexed": 0,
            "calendars_processed": 0,
            "errors": 0,
        }
        
        # Get all calendars that have been indexed
        calendar_ids = self.indexing_state.get_calendar_ids()
        
        # Also check for new calendars
        all_history_files = self.storage.list_history_files("calendar")
        all_calendar_ids = set(context_id for context_id, _, _ in all_history_files)
        
        for calendar_id in all_calendar_ids:
            try:
                last_indexed = self.indexing_state.get_last_indexed_date(calendar_id)
                
                # Get files to process
                history_files = self.storage.list_history_files("calendar")
                calendar_files = [
                    (date_str, file_path)
                    for ctx_id, date_str, file_path in history_files
                    if ctx_id == calendar_id
                ]
                
                # Filter to files after last indexed date
                if last_indexed:
                    calendar_files = [
                        (date_str, file_path)
                        for date_str, file_path in calendar_files
                        if date_str >= last_indexed
                    ]
                
                if not calendar_files:
                    continue
                
                logger.info(f"Processing {len(calendar_files)} new files for calendar: {calendar_id}")
                
                calendar_stats = self._ingest_calendar(calendar_id, calendar_files, force_reindex=False)
                stats["documents_processed"] += calendar_stats["documents_processed"]
                stats["documents_indexed"] += calendar_stats["documents_indexed"]
                stats["calendars_processed"] += 1
            except Exception as e:
                logger.error(f"Error processing calendar {calendar_id}: {e}")
                stats["errors"] += 1
        
        logger.info(f"Incremental ingestion complete: {stats}")
        return stats
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ingestion and indexing statistics."""
        indexing_stats = self.indexing_state.get_stats()
        vector_store_count = self.vector_store.get_count()
        
        return {
            "indexing": indexing_stats,
            "vector_store": {
                "document_count": vector_store_count,
            },
        }

