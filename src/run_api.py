#!/usr/bin/env python3
"""
Run the CivicForge API server
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from api.main import app

if __name__ == "__main__":
    print("Starting CivicForge API server...")
    print("API documentation will be available at: http://localhost:8000/docs")
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )