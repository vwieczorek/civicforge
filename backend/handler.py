"""
AWS Lambda handler for CivicForge API
"""

from mangum import Mangum
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from src.routes import router as quest_router
from src.models import ErrorResponse

# Create FastAPI app
app = FastAPI(
    title="CivicForge API",
    description="Peer-to-peer trust through dual-attestation",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
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
async def http_exception_handler(request, exc):
    return ErrorResponse(
        error=exc.detail,
        status_code=exc.status_code,
        timestamp=datetime.utcnow()
    )

# Lambda handler
handler = Mangum(app, lifespan="off")