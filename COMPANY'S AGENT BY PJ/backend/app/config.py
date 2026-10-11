"""Central configuration. Everything tunable lives here and can be
overridden from a .env file next to the backend folder."""
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage")))
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.2

    # --- Embeddings ---
    # "local" = sentence-transformers on your CPU (free, private)
    # "gemini" = Google embedding API (needs the API key)
    embeddings_provider: str = "local"
    embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    gemini_embedding_model: str = "text-embedding-004"

    # --- Chunking ---
    chunk_size: int = 900          # max characters per chunk
    chunk_overlap: int = 150       # character overlap between chunks

    # --- Retrieval ---
    retrieval_k: int = 8           # candidates fetched per retriever
    final_k: int = 5               # chunks kept after fusion + reranking
    rerank_enabled: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rrf_k: int = 60                # standard reciprocal-rank-fusion constant

    # --- Agent behaviour ---
    max_agent_retries: int = 1     # extra retrieval attempts if nothing relevant
    web_search_enabled: bool = True
    max_history_messages: int = 8  # chat memory window

    # --- Security & Limits ---
    max_upload_size_mb: int = 25   # maximum PDF upload size in megabytes

    # --- Server ---
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://localhost:8000,http://127.0.0.1:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "uploads").mkdir(exist_ok=True)
