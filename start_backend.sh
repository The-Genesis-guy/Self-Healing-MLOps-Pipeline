#!/bin/bash

# Start Backend API Server
# This script starts the FastAPI backend on port 8000

echo "🚀 Starting Self-Healing MLOps Backend API..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the API server
echo "🌐 Starting API server on http://localhost:8000"
echo "📚 API docs available at http://localhost:8000/docs"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

uvicorn api.main:app --reload --port 8000
