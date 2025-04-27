#!/bin/bash

echo "Checking backend status..."

# Check if backend/.env file exists
if [ ! -f "backend/.env" ]; then
  echo "Creating backend/.env file..."
  mkdir -p backend
  cat > backend/.env << ENVEOF
# Database settings
DATABASE_URL=sqlite:///./invoice_validator.db

# Gemini AI settings - replace with your actual API key
GEMINI_API_KEY=AIzaSyCCf1j-n_I_lsrWbW9WYkuxTTYZe3VuChg
GEMINI_MODEL=gemini-2.0-flash
CONFIDENCE_THRESHOLD=0.7

# Logging settings
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# File upload settings
UPLOAD_DIR=uploads
MAX_FILE_SIZE=10485760
ENVEOF
  echo "Created .env file. Edit it to add your Gemini API key."
else
  echo "Backend .env file exists, checking for missing fields..."
  # Check if CONFIDENCE_THRESHOLD exists, add if missing
  grep -q "CONFIDENCE_THRESHOLD" backend/.env || echo "CONFIDENCE_THRESHOLD=0.7" >> backend/.env
  echo "Updated .env file if needed."
fi

# Check for required directories
cd backend
if [ ! -d "logs" ]; then
  mkdir -p logs
  echo "Created logs directory."
fi

if [ ! -d "uploads" ]; then
  mkdir -p uploads
  echo "Created uploads directory."
fi

# Check if backend is running
echo "Checking if backend is running..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 2>/dev/null) || response="Failed"
if [ "$response" = "200" ]; then
  echo "Backend is running."
else
  echo "Backend is not running or returning errors (response: $response). Let's check for issues."
fi

# Check Python environment
echo "Checking Python environment..."
if command -v python3 &> /dev/null; then
  echo "Python found: $(python3 --version)"
else
  echo "Python not found. Please install Python 3."
fi

# Check required packages
echo "Checking if FastAPI and other required packages are installed..."
pip list 2>/dev/null | grep -E "fastapi|pydantic|uvicorn|sqlalchemy" || {
  echo "Some required packages may be missing."
  echo "Try installing them with:"
  echo "pip install fastapi pydantic uvicorn sqlalchemy pydantic-settings"
}

echo "Done checking backend status." 