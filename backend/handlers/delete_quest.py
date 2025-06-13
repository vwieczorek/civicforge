"""
Handler specifically for deleting quests
"""

from mangum import Mangum
from src.app_factory import create_app
from src.routers.quests_delete import router as delete_quest_router

# Create a specific FastAPI app for this handler
app = create_app(
    routers=[delete_quest_router],
    title="CivicForge API - Delete Quest",
    description="Handler for deleting quests"
)

# Lambda handler
handler = Mangum(app, lifespan="off")