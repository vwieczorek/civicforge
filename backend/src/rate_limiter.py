"""
Rate limiting configuration for API endpoints
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

async def key_func(request: Request) -> str:
    """
    Rate limit by IP address to prevent user-specific DoS attacks.
    
    Note: Per-user rate limiting would require authentication to happen first,
    which would need architectural changes. IP-based limiting is the secure default.
    """
    # Use IP address for rate limiting to prevent DoS via forged JWTs
    return f"ip:{get_remote_address(request)}"


# Create the limiter instance with our custom key function
limiter = Limiter(key_func=key_func)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded errors"""
    response = exc.detail
    logger.warning(
        f"Rate limit exceeded for {request.client.host}: {response}",
        extra={
            "ip": request.client.host,
            "path": request.url.path,
            "method": request.method
        }
    )
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: {response}",
            "error": "rate_limit_exceeded"
        },
    )


# Define rate limits for different endpoint types
RATE_LIMITS = {
    # Default limit for all endpoints
    "default": "100/minute",
    
    # Stricter limits for expensive operations
    "create_quest": "5/minute",
    "attest_quest": "10/minute",
    "claim_quest": "20/minute",
    "submit_quest": "10/minute",
    "dispute_quest": "5/minute",
    
    # More relaxed limits for read operations
    "read_operations": "200/minute",
    
    # Very strict limit for wallet updates
    "update_wallet": "3/minute",
}