"""
Quest creation operations router
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import datetime
import uuid

from ..models import Quest, QuestStatus, QuestCreate
from ..auth import get_current_user_id
from ..db import get_db_client, DynamoDBClient
from ..config import settings
from ..logger import logger, tracer
from ..rate_limiter import limiter, RATE_LIMITS
from ..sanitizer import sanitize_quest_title, sanitize_quest_description

router = APIRouter(tags=["quests"])


@router.post("/quests", response_model=Quest, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMITS["create_quest"])
@tracer.capture_method
async def create_quest(
    request: Request,
    quest: QuestCreate,
    user_id: str = Depends(get_current_user_id),
    db: DynamoDBClient = Depends(get_db_client)
) -> Quest:
    """Create a new quest"""
    logger.info("Creating new quest", extra={
        "user_id": user_id,
        "quest_title": quest.title,
        "reward": quest.reward
    })
    
    # Check if user has enough points (anti-spam)
    user = await db.get_user(user_id)
    if not user:
        logger.warning("User not found during quest creation", extra={"user_id": user_id})
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.questCreationPoints < settings.quest_creation_cost:
        logger.warning("Insufficient quest creation points", extra={
            "user_id": user_id,
            "available_points": user.questCreationPoints,
            "required_points": settings.quest_creation_cost
        })
        raise HTTPException(
            status_code=429, 
            detail=f"Insufficient quest creation points. You have {user.questCreationPoints} but need {settings.quest_creation_cost}."
        )
    
    # Deduct points atomically
    success = await db.deduct_quest_creation_points(user_id, settings.quest_creation_cost)
    if not success:
        logger.error("Failed to deduct quest creation points", extra={
            "user_id": user_id,
            "points_to_deduct": settings.quest_creation_cost
        })
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
    
    # Explicitly sanitize user-provided content before saving
    quest_data["title"] = sanitize_quest_title(quest_data["title"])
    quest_data["description"] = sanitize_quest_description(quest_data["description"])
    
    # Create Quest object
    new_quest = Quest(**quest_data)
    await db.create_quest(new_quest)
    
    logger.info("Quest created successfully", extra={
        "quest_id": new_quest.questId,
        "creator_id": user_id,
        "title": new_quest.title,
        "reward": new_quest.reward
    })
    
    return new_quest