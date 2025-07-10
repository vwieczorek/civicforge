#!/bin/bash
# CivicForge Demo Launcher - One-click setup and run

echo "🏛️  CivicForge Demo"
echo "=================="
echo

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required"
    echo "Please install Python 3.7 or later"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "src/api/main.py" ]; then
    echo "❌ Error: Please run this script from the CivicForge root directory"
    exit 1
fi

# Check/create virtual environment
if [ ! -d "src/venv" ]; then
    echo "📦 Setting up Python environment..."
    python3 -m venv src/venv
fi

# Activate virtual environment
source src/venv/bin/activate

# Install/update dependencies
echo "📦 Checking dependencies..."
pip install -q -r src/requirements-dev.txt 2>/dev/null || {
    echo "Installing dependencies (this may take a minute on first run)..."
    pip install -r src/requirements-dev.txt
}

# Run the interactive demo
echo
echo "✨ Starting CivicForge..."
echo
python try_civicforge.py