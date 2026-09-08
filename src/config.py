import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    # LLM 1 - Knowledge Builder (Extraction & Normalization)
    EXTRACTION_LLM_PROVIDER: str = os.getenv("EXTRACTION_LLM_PROVIDER", "google")
    EXTRACTION_LLM_API_KEY: str = os.getenv("EXTRACTION_LLM_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    EXTRACTION_LLM_MODEL: str = os.getenv("EXTRACTION_LLM_MODEL", os.getenv("LLM_MODEL_NAME", "gemini-3.6-flash"))

    # LLM 2 - Independent Reasoner (Cross-Document Judgment)
    REASONING_LLM_PROVIDER: str = os.getenv("REASONING_LLM_PROVIDER", "google")
    REASONING_LLM_API_KEY: str = os.getenv("REASONING_LLM_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    REASONING_LLM_MODEL: str = os.getenv("REASONING_LLM_MODEL", "gemini-3.6-flash")

    # Fallback keys if generic names are used
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Embedding and Vector Storage
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "local")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    
    # Database Settings (PostgreSQL + pgvector or fallback SQLite)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./fact_knowledge.db")

    # Retrieval & Matching Settings
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.50"))
    TOP_K_CANDIDATES: int = int(os.getenv("TOP_K_CANDIDATES", "2"))

    # Chunking Settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "4000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "500"))

    # Directories & Pipeline
    UPLOAD_DIR: Path = Path("./data/uploads")
    DEMO_DIR: Path = Path("./data/demo_pdfs")
    CLEANUP_AFTER_PROCESSING: bool = True

# Compatibility handling for legacy code
settings = Settings()

# Attach legacy attributes to settings for backward compatibility
settings.LLM_PROVIDER = settings.EXTRACTION_LLM_PROVIDER
settings.LLM_MODEL_NAME = settings.EXTRACTION_LLM_MODEL
settings.GOOGLE_API_KEY = settings.EXTRACTION_LLM_API_KEY

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.DEMO_DIR.mkdir(parents=True, exist_ok=True)
