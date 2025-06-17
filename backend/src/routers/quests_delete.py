"""
Quest deletion operations router
"""

from fastapi import APIRouter, Depends, HTTPException, status
import logging

from ..models import QuestStatus
from ..auth import get_current_user_id
from ..db import get_db_client, DynamoDBClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["quests"])

# Constants for anti-spam
QUEST_CREATION_COST = 1  # Points to refund when quest is deleted


@router.delete("/quests/{quest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quest(
    quest_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DynamoDBClient = Depends(get_db_client)
) -> None:
    """Delete a quest - only allowed by creator and only if unclaimed"""
    # First check if quest exists
    quest = await db.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    # Check authorization
    if quest.creatorId != user_id:
        raise HTTPException(
            status_code=403, 
            detail="Only the quest creator can delete a quest"
        )
    
    # Check if quest can be deleted (only OPEN quests)
    if quest.status != QuestStatus.OPEN:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete quest in {quest.status.value} status. Only OPEN quests can be deleted."
        )
    
    # Attempt atomic delete with conditions
    success = await db.delete_quest_atomic(quest_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=409,
            detail="Unable to delete quest. It may have been claimed or modified."
        )
    
    # Refund quest creation points since quest was never completed
    await db.award_quest_points(user_id, QUEST_CREATION_COST)
    
    return None