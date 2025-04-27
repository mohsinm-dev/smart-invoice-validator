from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Invoice Validator"
    API_V1_STR: str = "/api/v1"
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./invoice_validator.db"
    
    # Gemini AI settings
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash"
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # File upload settings
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {".pdf", ".doc", ".docx"}
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create necessary directories
def create_directories():
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

settings = Settings()
create_directories() 