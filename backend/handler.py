"""
Legacy handler - now split into separate handlers for security

IMPORTANT: This file is kept for backwards compatibility and local development only.
In production, each Lambda function uses its own handler from the handlers/ directory
to enforce proper IAM role isolation.

See:
- handlers/api.py - General API operations (read, claim, submit)
- handlers/create_quest.py - Quest creation
- handlers/attest_quest.py - Quest attestation and rewards
- handlers/delete_quest.py - Quest deletion

For local development, this imports the general API handler which includes
most routes except the high-privilege operations.
"""

import warnings

# Show deprecation warning in development
warnings.warn(
    "handler.py is deprecated. Use specific handlers from handlers/ directory.",
    DeprecationWarning,
    stacklevel=2
)

# For local development/testing, import the general API handler
try:
    from handlers.api import handler, app
except ImportError:
    # Fallback for tests that might import this directly
    from mangum import Mangum
    from src.app_factory import create_app
    from src.routers.quests_read import router as quests_read_router
    from src.routers.quests_actions import router as quests_actions_router
    from src.routers.users import router as users_router
    from src.routers.system import router as system_router
    
    app = create_app(
        routers=[
            quests_read_router,
            quests_actions_router,
            users_router,
            system_router
        ],
        title="CivicForge API - Local Development",
        description="Development handler - DO NOT USE IN PRODUCTION"
    )
    
    handler = Mangum(app, lifespan="off")

__all__ = ['handler', 'app']