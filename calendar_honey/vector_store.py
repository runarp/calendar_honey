"""Vector store interface for storing and querying RAG documents."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from .config import Config

logger = logging.getLogger(__name__)


class VectorStore:
    """Interface for vector store operations."""
    
    def __init__(self, config: Config):
        self.config = config
        self.vs_config = config.vector_store
        self.collection = None
        self._initialize_store()
    
    def _initialize_store(self) -> None:
        """Initialize the vector store."""
        if self.vs_config.type == "chroma":
            self._initialize_chroma()
        else:
            raise ValueError(f"Unsupported vector store type: {self.vs_config.type}")
    
    def _initialize_chroma(self) -> None:
        """Initialize ChromaDB vector store."""
        try:
            import chromadb
        except ImportError:
            raise ImportError("chromadb is required. Install with: pip install chromadb")
        
        # Create persistent client
        persist_directory = str(Path(self.vs_config.path).expanduser())
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initializing ChromaDB at {persist_directory}")
        
        # Try to initialize without Settings first (for Python 3.14 compatibility)
        try:
            self.client = chromadb.PersistentClient(path=persist_directory)
        except Exception:
            # Fallback: try with Settings if available
            try:
                from chromadb.config import Settings
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(anonymized_telemetry=False)
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {e}")
                raise
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.vs_config.collection_name,
            metadata={"description": "Calendar events for RAG"}
        )
        
        logger.info(f"Using collection: {self.vs_config.collection_name}")
    
    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        """Add documents to the vector store."""
        if not documents:
            return
        
        if len(documents) != len(embeddings):
            raise ValueError("Documents and embeddings must have the same length")
        
        if self.vs_config.type == "chroma":
            self._add_to_chroma(documents, embeddings)
        else:
            raise ValueError(f"Unsupported vector store type: {self.vs_config.type}")
    
    def _add_to_chroma(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        """Add documents to ChromaDB."""
        ids = [doc["id"] for doc in documents]
        contents = [doc["content"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]
        
        # ChromaDB requires metadata values to be strings, numbers, or bools
        # Convert any complex objects to JSON strings
        cleaned_metadatas = []
        for metadata in metadatas:
            cleaned = {}
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    cleaned[key] = value
                elif isinstance(value, list):
                    # Convert list to comma-separated string for simple lists
                    if all(isinstance(item, str) for item in value):
                        cleaned[key] = ",".join(value)
                    else:
                        cleaned[key] = json.dumps(value)
                else:
                    cleaned[key] = json.dumps(value)
            cleaned_metadatas.append(cleaned)
        
        try:
            # Check if documents already exist
            existing_ids = set(self.collection.get(ids=ids)["ids"])
            new_ids = [doc_id for doc_id in ids if doc_id not in existing_ids]
            
            if not new_ids:
                logger.debug(f"All {len(ids)} documents already exist in vector store")
                return
            
            # Filter to only new documents
            new_indices = [i for i, doc_id in enumerate(ids) if doc_id in new_ids]
            new_documents = [documents[i] for i in new_indices]
            new_embeddings = [embeddings[i] for i in new_indices]
            new_metadatas = [cleaned_metadatas[i] for i in new_indices]
            new_ids_list = [ids[i] for i in new_indices]
            new_contents = [contents[i] for i in new_indices]
            
            # Add only new documents
            self.collection.add(
                ids=new_ids_list,
                embeddings=new_embeddings,
                documents=new_contents,
                metadatas=new_metadatas,
            )
            
            logger.info(f"Added {len(new_documents)} new documents to vector store")
        except Exception as e:
            logger.error(f"Error adding documents to ChromaDB: {e}")
            raise
    
    def query(
        self,
        query_text: str,
        query_embedding: List[float],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query the vector store."""
        if self.vs_config.type == "chroma":
            return self._query_chroma(query_text, query_embedding, n_results, where)
        else:
            raise ValueError(f"Unsupported vector store type: {self.vs_config.type}")
    
    def _query_chroma(
        self,
        query_text: str,
        query_embedding: List[float],
        n_results: int,
        where: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Query ChromaDB."""
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
            )
            
            # Format results
            documents = []
            for i in range(len(results["ids"][0])):
                doc = {
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None,
                }
                documents.append(doc)
            
            return documents
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}")
            raise
    
    def delete(self, ids: List[str]) -> None:
        """Delete documents from the vector store."""
        if self.vs_config.type == "chroma":
            self.collection.delete(ids=ids)
        else:
            raise ValueError(f"Unsupported vector store type: {self.vs_config.type}")
    
    def get_count(self) -> int:
        """Get the total number of documents in the vector store."""
        if self.vs_config.type == "chroma":
            return self.collection.count()
        else:
            raise ValueError(f"Unsupported vector store type: {self.vs_config.type}")
    
    def get_all_ids(self) -> List[str]:
        """Get all document IDs in the vector store."""
        if self.vs_config.type == "chroma":
            # ChromaDB doesn't have a direct way to get all IDs, so we query for a large number
            results = self.collection.get(limit=999999)
            return results["ids"]
        else:
            raise ValueError(f"Unsupported vector store type: {self.vs_config.type}")

