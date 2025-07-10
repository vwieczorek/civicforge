#!/bin/bash
# CivicForge Prototype Demo Script
# This script starts both the Remote Thinker and Local Controller for easy demonstration

echo "🏛️  Starting CivicForge Prototype Demo"
echo "===================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not found"
    echo "Please install Python 3.7+ to run the Remote Thinker"
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is required but not found"
    echo "Please install Node.js 14+ to run the Local Controller"
    exit 1
fi

# Set up virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Install dependencies
echo "📦 Installing required Python packages..."
./venv/bin/pip install -r requirements.txt -q || {
    echo "❌ Error: Failed to install Python packages"
    exit 1
}

# Start Remote Thinker in background
echo "🚀 Starting Remote Thinker (AI Service)..."
./venv/bin/python server.py &
REMOTE_PID=$!

# Give Remote Thinker time to start
echo "⏳ Waiting for Remote Thinker to initialize..."
sleep 3

# Check if Remote Thinker started successfully
if ! curl -s http://localhost:8000/ > /dev/null; then
    echo "❌ Error: Remote Thinker failed to start"
    kill $REMOTE_PID 2>/dev/null
    exit 1
fi

echo "✅ Remote Thinker is running!"
echo ""
echo "🎯 Starting Local Controller (User Interface)..."
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down CivicForge prototype..."
    kill $REMOTE_PID 2>/dev/null
    exit 0
}

# Set up cleanup on script exit
trap cleanup EXIT INT TERM

# Start Local Controller in foreground
node local.js

# This line is reached when Local Controller exits
cleanup