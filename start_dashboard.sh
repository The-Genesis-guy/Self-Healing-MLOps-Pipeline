#!/bin/bash

# Start Dashboard Development Server
# This script starts the React dashboard on port 5173

echo "🎨 Starting Self-Healing MLOps Dashboard..."
echo ""

# Check if node_modules exists
if [ ! -d "dashboard/node_modules" ]; then
    echo "📦 Installing dashboard dependencies..."
    cd dashboard
    npm install
    cd ..
fi

# Start the dashboard
echo "🌐 Starting dashboard on http://localhost:5173"
echo ""
echo "⚠️  Make sure the backend API is running on port 8000!"
echo "   Run ./start_backend.sh in another terminal"
echo ""
echo "Press CTRL+C to stop the dashboard"
echo ""

cd dashboard
npm run dev
