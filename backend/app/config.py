import os
from pathlib import Path
from dotenv import load_dotenv

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

# API Configuration
API_PREFIX = "/api/v1"

# File upload settings
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# AI/OCR configuration
OCR_MODEL = os.getenv("OCR_MODEL", "gpt-4o-mini")
OCR_API_KEY = os.getenv("OPENAI_API_KEY", "")  # API key for OpenAI