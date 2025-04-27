#!/bin/bash

echo "Starting development environment..."

# Start backend in background
cd backend
echo "Starting FastAPI server..."
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
cd ../frontend
echo "Starting Next.js frontend..."
npm run dev

# Kill backend when script exits
trap "kill $BACKEND_PID" EXIT

# Wait for any key press to exit
echo "Press any key to stop development environment..."
read -n 1 -s 