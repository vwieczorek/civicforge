#!/bin/bash
# Launch CivicForge Demo with Authentication

echo "🏛️  CivicForge - Connect with Your Community"
echo "==========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if API is already running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ CivicForge API is already running${NC}"
else
    echo "📌 Starting CivicForge API..."
    
    # Ensure Redis is running
    if ! command -v redis-server &> /dev/null; then
        echo -e "${RED}❌ 'redis-server' command not found. Please install Redis.${NC}"
        echo "   brew install redis  (macOS)"
        echo "   sudo apt-get install redis-server  (Ubuntu)"
        exit 1
    fi
    
    if command -v redis-cli &> /dev/null && ! redis-cli ping > /dev/null 2>&1; then
        echo "Starting Redis..."
        redis-server --daemonize yes
        sleep 1
        if ! redis-cli ping > /dev/null 2>&1; then
            echo -e "${RED}❌ Failed to start Redis. Please check your Redis installation.${NC}"
            exit 1
        fi
    fi
    
    # Start API in background
    cd ../src
    if [ ! -d "venv" ]; then
        echo "Setting up environment..."
        python3 -m venv venv
        ./venv/bin/pip install -r requirements-dev.txt -q
    fi
    
    # Ensure .env exists
    if [ ! -f "../.env" ]; then
        cp ../.env.example ../.env
    fi
    
    echo "Starting API server..."
    PYTHONPATH=$PWD ./venv/bin/python -m api.main_with_auth > ../try-it/api.log 2>&1 &
    API_PID=$!
    
    # Set up cleanup immediately after starting process
    trap cleanup EXIT
    
    # Wait for API to start
    echo "Waiting for API to initialize..."
    for i in {1..10}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API is ready!${NC}"
            break
        fi
        sleep 1
    done
    
    cd ../try-it
fi

echo ""
echo "🚀 Launching CivicForge Demo"
echo "──────────────────────────"
echo ""
echo -e "${YELLOW}When prompted for email, just press Enter to use the demo account.${NC}"
echo -e "${YELLOW}Watch this terminal for your secure connection link!${NC}"
echo ""

# Run the demo
python3 civic_demo.py

# Cleanup function
cleanup() {
    if [ ! -z "$API_PID" ]; then
        echo ""
        echo "Stopping API server..."
        kill $API_PID 2>/dev/null
    fi
}

