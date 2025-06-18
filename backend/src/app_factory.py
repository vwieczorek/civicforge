"""
FastAPI Application Factory for creating isolated Lambda handlers
"""

import os
import json
import logging
import traceback
from fastapi import FastAPI, HTTPException, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List

from .rate_limiter import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def create_app(
    routers: List[APIRouter], 
    title: str, 
    description: str,
    include_health: bool = True
) -> FastAPI:
    """
    Factory to create and configure a FastAPI application instance.
    
    Args:
        routers: List of APIRouter instances to include
        title: Application title
        description: Application description
        include_health: Whether to include the health check endpoint
    
    Returns:
        Configured FastAPI application
    """
    
    app = FastAPI(
        title=title,
        description=description,
        version="1.0.0"
    )
    
    # Add rate limiter to the app state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Configure CORS with specific headers (fixing the wildcard security issue)
    allowed_origins = os.environ.get("FRONTEND_URL", "http://localhost:5173").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key", "X-Amz-Security-Token"],
    )

    # Health check endpoint (common to all handlers)
    if include_health:
        health_router = APIRouter()
        
        @health_router.get("/health", tags=["system"])
        async def health_check():
            return {
                "status": "healthy", 
                "timestamp": datetime.utcnow().isoformat(),
                "function": os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "local")
            }
        
        app.include_router(health_router)

    # Include specific routers passed to the factory
    for router in routers:
        app.include_router(router, prefix="/api/v1")

    # Register common exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.error(json.dumps({
            "level": "ERROR",
            "error_type": "HTTPException",
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url.path),
            "method": request.method,
            "function": os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "local")
        }))
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        error_id = f"ERR-{datetime.utcnow().timestamp()}"
        
        # In production, don't expose full traceback
        is_production = os.environ.get("STAGE", "dev") == "prod"
        
        logger.error(json.dumps({
            "level": "ERROR",
            "error_type": "UnhandledException",
            "error_id": error_id,
            "exception": str(exc),
            "traceback": traceback.format_exc() if not is_production else "hidden",
            "path": str(request.url.path),
            "method": request.method,
            "function": os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "local")
        }))
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_id": error_id
            }
        )

    return app