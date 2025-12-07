#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for Python
if ! command_exists python3; then
    echo "Python 3 is required but not installed."
    exit 1
fi

# Check for Node.js
if ! command_exists npm; then
    echo "Node.js (npm) is required but not installed."
    exit 1
fi

echo "Setting up Backend..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
cd ..

echo "Setting up Frontend..."
cd frontend
npm install
cd ..

echo "Starting Application..."

# Trap to kill background processes on exit
trap 'kill 0' EXIT

# Start Backend
cd backend
source venv/bin/activate
echo "Starting Backend on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start Frontend
cd frontend
echo "Starting Frontend..."
npm run dev &
FRONTEND_PID=$!
cd ..

wait
