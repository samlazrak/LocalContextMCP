#!/bin/bash

# Local IDE Startup Script
# This script starts the Local IDE server

echo "🚀 Starting Local IDE - Cursor Alternative"
echo "========================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
echo "Checking dependencies..."
pip install -r requirements.txt > /dev/null 2>&1

# Start the IDE server
echo "Starting IDE server..."
echo "Opening browser to http://localhost:3000"
echo "Press Ctrl+C to stop the server"
echo "========================================"

# Open browser (optional)
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:3000 > /dev/null 2>&1 &
elif command -v open > /dev/null; then
    open http://localhost:3000 > /dev/null 2>&1 &
fi

# Start the server
python ide_server.py