"""
Configuration management for the Insurance AI Agent.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
POLICIES_DIR = DATA_DIR / "policies"
CUSTOMERS_DIR = DATA_DIR / "customers"
CHROMA_DIR = DATA_DIR / "chroma_db"
DATASET_DIR = BASE_DIR / "Dataset"  # Hackathon dataset with PDFs and Excel files


class OpenAIConfig(BaseModel):
    """OpenAI API configuration."""
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 1024


class ElevenLabsConfig(BaseModel):
    """ElevenLabs TTS configuration."""
    api_key: str = Field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY", ""))
    voice_id: str = Field(default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"))
    model: str = "eleven_turbo_v2"


class VectorDBConfig(BaseModel):
    """Vector database configuration."""
    persist_dir: Path = CHROMA_DIR
    collection_name: str = "insurance_policies"
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 500
    chunk_overlap: int = 50


class AgentConfig(BaseModel):
    """Agent behavior configuration."""
    max_iterations: int = 10
    response_timeout: float = 30.0
    enable_guardrails: bool = True
    escalation_threshold: int = 2  # Failed searches before escalation
    persona: str = "helpful, precise, compliant insurance expert"


class AppConfig(BaseModel):
    """Main application configuration."""
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "False").lower() == "true")
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    elevenlabs: ElevenLabsConfig = Field(default_factory=ElevenLabsConfig)
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)


# Global config instance
config = AppConfig()


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return config


def ensure_directories():
    """Ensure all required directories exist."""
    for dir_path in [DATA_DIR, POLICIES_DIR, CUSTOMERS_DIR, CHROMA_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)
