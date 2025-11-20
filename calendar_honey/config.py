"""Configuration management for calendar_honey."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable."""
    return os.environ.get(key, default)


@dataclass
class VectorStoreConfig:
    """Vector store configuration."""
    type: str = "chroma"  # chroma | qdrant | pinecone
    path: str = "/data/channels/honey/calendar/personal/vector_store"
    collection_name: str = "calendar_events"


@dataclass
class EmbeddingConfig:
    """Embedding service configuration."""
    provider: str = "sentence-transformers"  # sentence-transformers | openai | ollama
    model: str = "all-MiniLM-L6-v2"  # Default sentence-transformers model
    api_key: Optional[str] = None
    batch_size: int = 100


@dataclass
class TransformerConfig:
    """Document transformer configuration."""
    include_attendees: bool = True
    include_location: bool = True
    include_description: bool = True
    max_description_length: int = 2000


@dataclass
class IndexingConfig:
    """Indexing configuration."""
    mode: str = "incremental"  # full | incremental
    check_interval_seconds: int = 300
    reindex_on_startup: bool = False


@dataclass
class Config:
    """Main configuration for calendar_honey."""
    data_root: str = field(default="/data/channels")
    instance_id: str = field(default="personal")
    channel_type: str = field(default="calendar")
    
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    transformer: TransformerConfig = field(default_factory=TransformerConfig)
    indexing: IndexingConfig = field(default_factory=IndexingConfig)
    
    log_level: str = "INFO"
    health_port: int = 8081
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from YAML file and environment variables."""
        config_dict = {}
        
        # Load from YAML if provided
        if config_path and Path(config_path).exists() and yaml:
            with open(config_path, "r") as f:
                config_dict = yaml.safe_load(f) or {}
        
        # Environment variables override YAML
        data_root = get_env("DATA_ROOT", config_dict.get("data_root", "/data/channels"))
        if data_root and data_root.startswith("~"):
            data_root = str(Path(data_root).expanduser())
        
        # Vector store config
        vs_dict = config_dict.get("vector_store", {})
        vector_store = VectorStoreConfig(
            type=get_env("VECTOR_STORE_TYPE", vs_dict.get("type", "chroma")),
            path=get_env("VECTOR_STORE_PATH", vs_dict.get("path", f"{data_root}/honey/calendar/{get_env('INSTANCE_ID', config_dict.get('instance_id', 'personal'))}/vector_store")),
            collection_name=get_env("VECTOR_STORE_COLLECTION", vs_dict.get("collection_name", "calendar_events")),
        )
        
        # Embedding config
        emb_dict = config_dict.get("embedding", {})
        embedding = EmbeddingConfig(
            provider=get_env("EMBEDDING_PROVIDER", emb_dict.get("provider", "sentence-transformers")),
            model=get_env("EMBEDDING_MODEL", emb_dict.get("model", "all-MiniLM-L6-v2")),
            api_key=get_env("OPENAI_API_KEY", emb_dict.get("api_key")),
            batch_size=int(get_env("EMBEDDING_BATCH_SIZE", emb_dict.get("batch_size", 100))),
        )
        
        # Transformer config
        trans_dict = config_dict.get("transformer", {})
        transformer = TransformerConfig(
            include_attendees=trans_dict.get("include_attendees", True),
            include_location=trans_dict.get("include_location", True),
            include_description=trans_dict.get("include_description", True),
            max_description_length=trans_dict.get("max_description_length", 2000),
        )
        
        # Indexing config
        idx_dict = config_dict.get("indexing", {})
        indexing = IndexingConfig(
            mode=get_env("INDEXING_MODE", idx_dict.get("mode", "incremental")),
            check_interval_seconds=int(get_env("INDEXING_CHECK_INTERVAL", idx_dict.get("check_interval_seconds", 300))),
            reindex_on_startup=idx_dict.get("reindex_on_startup", False),
        )
        
        return cls(
            data_root=data_root,
            instance_id=get_env("INSTANCE_ID", config_dict.get("instance_id", "personal")),
            channel_type=get_env("CHANNEL_TYPE", config_dict.get("channel_type", "calendar")),
            vector_store=vector_store,
            embedding=embedding,
            transformer=transformer,
            indexing=indexing,
            log_level=get_env("LOG_LEVEL", config_dict.get("log_level", "INFO")),
            health_port=int(get_env("HEALTH_PORT", config_dict.get("health_port", 8081))),
        )
    
    @property
    def nest_path(self) -> Path:
        """Path to the Bee's Nest data directory."""
        return Path(self.data_root) / self.channel_type / self.instance_id
    
    @property
    def honey_path(self) -> Path:
        """Path to honey-specific storage."""
        return Path(self.data_root) / "honey" / self.channel_type / self.instance_id

