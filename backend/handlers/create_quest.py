"""
Handler specifically for creating quests
"""

from mangum import Mangum
from src.app_factory import create_app
from src.routers.quests_create import router as create_quest_router

# Create a specific FastAPI app for this handler
app = create_app(
    routers=[create_quest_router],
    title="CivicForge API - Create Quest",
    description="Handler for creating new quests"
)

# Lambda handler
handler = Mangum(app, lifespan="off")