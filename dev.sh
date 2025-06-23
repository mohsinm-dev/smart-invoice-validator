#!/bin/bash

echo "Starting development environment..."

# Check if backend/.env file exists
if [ ! -f "backend/.env" ]; then
  echo "Creating backend/.env file..."
  cat > backend/.env << EOF
# Database settings
DATABASE_URL=sqlite:///./invoice_validator.db

# Gemini AI settings - replace with your actual API key
GEMINI_API_KEY=AIzaSyCCf1j-n_I_lsrWbW9WYkuxTTYZe3VuChg
GEMINI_MODEL=gemini-2.0-flash

# Logging settings
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
EOF
  echo "Please edit backend/.env and add your actual Gemini API key"
  sleep 2
fi

# Start backend in background
cd backend
echo "Starting FastAPI server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Give the backend time to start
echo "Waiting for backend to start..."
sleep 3

# Start frontend
cd ../frontend
echo "Starting Next.js frontend..."
npm run dev

# Kill backend when script exits
trap "kill $BACKEND_PID" EXIT

# Wait for any key press to exit
echo "Press any key to stop development environment..."
read -n 1 -s 