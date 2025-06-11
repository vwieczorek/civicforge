#!/bin/bash

# Test runner script for CivicForge
set -e

echo "🧪 Running CivicForge tests..."

# Backend tests
echo "📦 Running backend tests..."
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio
pytest -v

# Check for test failures
if [ $? -eq 0 ]; then
    echo "✅ Backend tests passed!"
else
    echo "❌ Backend tests failed!"
    exit 1
fi

cd ..

# Frontend build test
echo "📦 Testing frontend build..."
cd frontend
npm install
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Frontend build successful!"
else
    echo "❌ Frontend build failed!"
    exit 1
fi

cd ..

echo ""
echo "🎉 All tests passed!"