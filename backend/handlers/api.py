"""
General API handler for read operations and non-privileged actions
"""

from mangum import Mangum
from src.app_factory import create_app
from src.routers.quests_read import router as quests_read_router
from src.routers.quests_actions import router as quests_actions_router
from src.routers.users import router as users_router
from src.routers.system import router as system_router

# Create a specific FastAPI app for this handler
app = create_app(
    routers=[
        quests_read_router,
        quests_actions_router,  # claim, submit, dispute
        users_router,
        system_router
    ],
    title="CivicForge API - General",
    description="Handler for general read and non-critical operations"
)

# Lambda handler
handler = Mangum(app, lifespan="off")