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

echo "📦 Running frontend tests..."
if npm test; then
    echo "✅ Frontend tests passed!"
else
    echo "❌ Frontend tests failed!"
    exit 1
fi

cd ..

echo ""
echo "🎉 All tests passed!"