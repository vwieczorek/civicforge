"""
Quest creation operations router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
import uuid
import logging

from ..models import Quest, QuestStatus, QuestCreate
from ..auth import get_current_user_id
from ..db import db_client
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["quests"])


@router.post("/quests", response_model=Quest, status_code=status.HTTP_201_CREATED)
async def create_quest(
    quest: QuestCreate,
    user_id: str = Depends(get_current_user_id)
) -> Quest:
    """Create a new quest"""
    # Check if user has enough points (anti-spam)
    user = await db_client.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.questCreationPoints < settings.quest_creation_cost:
        raise HTTPException(
            status_code=429, 
            detail=f"Insufficient quest creation points. You have {user.questCreationPoints} but need {settings.quest_creation_cost}."
        )
    
    # Deduct points atomically
    success = await db_client.deduct_quest_creation_points(user_id, settings.quest_creation_cost)
    if not success:
        raise HTTPException(
            status_code=429,
            detail="Unable to create quest. Please try again later."
        )
    
    quest_data = quest.dict()
    quest_data["questId"] = str(uuid.uuid4())
    quest_data["creatorId"] = user_id
    quest_data["status"] = QuestStatus.OPEN
    quest_data["attestations"] = []
    quest_data["createdAt"] = datetime.utcnow()
    quest_data["updatedAt"] = datetime.utcnow()
    
    # Create Quest object
    new_quest = Quest(**quest_data)
    await db_client.create_quest(new_quest)
    return new_quest