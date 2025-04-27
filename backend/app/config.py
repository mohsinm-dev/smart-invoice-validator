import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Set

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CONTRACTS_DIR = DATA_DIR / "contracts"
TEMP_DIR = DATA_DIR / "temp"

# Ensure directories exist
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    # API Configuration
    API_PREFIX: str = "/api/v1"
    
    # File upload settings
    ALLOWED_EXTENSIONS_STR: str = "pdf,png,jpg,jpeg"
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
    
    # Document Processor configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    @property
    def ALLOWED_EXTENSIONS(self) -> Set[str]:
        return set(self.ALLOWED_EXTENSIONS_STR.split(","))
    
    class Config:
        env_file = os.path.join(BASE_DIR, ".env")
        env_file_encoding = "utf-8"

# Create settings instance
settings = Settings()