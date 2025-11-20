"""Embedding service for generating vector embeddings."""

import logging
from typing import List, Optional
from .config import Config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings from text."""
    
    def __init__(self, config: Config):
        self.config = config
        self.embedding_config = config.embedding
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self) -> None:
        """Initialize the embedding model."""
        provider = self.embedding_config.provider
        model_name = self.embedding_config.model
        
        if provider == "sentence-transformers":
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading sentence-transformers model: {model_name}")
                self.model = SentenceTransformer(model_name)
                logger.info("Model loaded successfully")
            except ImportError:
                raise ImportError("sentence-transformers is required. Install with: pip install sentence-transformers")
        
        elif provider == "openai":
            # OpenAI embeddings are handled via API calls
            if not self.embedding_config.api_key:
                raise ValueError("OpenAI API key is required for OpenAI embeddings")
            self.model = "openai"
            logger.info("Using OpenAI embeddings")
        
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not text:
            # Return zero vector for empty text (dimension depends on model)
            return [0.0] * self.get_embedding_dimension()
        
        if self.embedding_config.provider == "sentence-transformers":
            if self.model is None:
                raise RuntimeError("Model not initialized")
            embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
            return embedding.tolist()
        
        elif self.embedding_config.provider == "openai":
            return self._openai_embed(text)
        
        else:
            raise ValueError(f"Unknown provider: {self.embedding_config.provider}")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        if not texts:
            return []
        
        if self.embedding_config.provider == "sentence-transformers":
            if self.model is None:
                raise RuntimeError("Model not initialized")
            
            # Filter out empty texts
            non_empty_texts = [t if t else " " for t in texts]
            
            embeddings = self.model.encode(
                non_empty_texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=self.embedding_config.batch_size,
                show_progress_bar=False,
            )
            return embeddings.tolist()
        
        elif self.embedding_config.provider == "openai":
            return [self._openai_embed(text) for text in texts]
        
        else:
            raise ValueError(f"Unknown provider: {self.embedding_config.provider}")
    
    def _openai_embed(self, text: str) -> List[float]:
        """Generate OpenAI embedding."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.embedding_config.api_key)
            
            response = client.embeddings.create(
                model=self.embedding_config.model,
                input=text,
            )
            return response.data[0].embedding
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        if self.embedding_config.provider == "sentence-transformers":
            if self.model is None:
                # Default dimension for common models
                return 384
            return self.model.get_sentence_embedding_dimension()
        
        elif self.embedding_config.provider == "openai":
            # OpenAI text-embedding-3-small: 1536
            # text-embedding-3-large: 3072
            if "large" in self.embedding_config.model.lower():
                return 3072
            return 1536
        
        else:
            return 384  # Default fallback

