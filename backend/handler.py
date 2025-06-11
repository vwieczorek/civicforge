"""
AWS Lambda handler for CivicForge API
"""

import os
import json
import logging
import traceback
from mangum import Mangum
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

from src.routes import router as quest_router

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create FastAPI app
app = FastAPI(
    title="CivicForge API",
    description="Peer-to-peer trust through dual-attestation",
    version="1.0.0"
)

# Configure CORS with environment-based origins
ALLOWED_ORIGINS = os.environ.get("FRONTEND_URL", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "civicforge-api"
    }

# Include routers
app.include_router(quest_router, prefix="/api/v1", tags=["quests"])

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Log structured error for CloudWatch metric filter
    logger.error(json.dumps({
        "level": "ERROR",
        "error_type": "HTTPException",
        "status_code": exc.status_code,
        "detail": exc.detail,
        "path": str(request.url.path),
        "method": request.method,
        "timestamp": datetime.utcnow().isoformat()
    }))
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Log structured error for CloudWatch metric filter
    error_id = f"ERR-{datetime.utcnow().timestamp()}"
    logger.error(json.dumps({
        "level": "ERROR",
        "error_type": "UnhandledException",
        "error_id": error_id,
        "exception": str(exc),
        "traceback": traceback.format_exc(),
        "path": str(request.url.path),
        "method": request.method,
        "timestamp": datetime.utcnow().isoformat()
    }))
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Lambda handler
handler = Mangum(app, lifespan="off")