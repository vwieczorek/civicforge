"""
Handler specifically for quest attestation
"""

from mangum import Mangum
from src.app_factory import create_app
from src.routers.quests_attest import router as attest_quest_router

# Create a specific FastAPI app for this handler
app = create_app(
    routers=[attest_quest_router],
    title="CivicForge API - Attest Quest",
    description="Handler for quest attestation and completion"
)

# Lambda handler
handler = Mangum(app, lifespan="off")