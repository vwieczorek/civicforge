"""
Read-only quest operations router
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
import logging

from ..models import Quest, QuestStatus
from ..auth import require_auth
from ..db import db_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["quests"])


@router.get("/quests", response_model=List[Quest])
async def list_quests(
    status: Optional[QuestStatus] = None,
    _: str = Depends(require_auth)
) -> List[Quest]:
    """List all quests, optionally filtered by status"""
    try:
        quests = await db_client.list_quests(status=status)
        return quests
    except Exception as e:
        logger.error(f"Failed to list quests: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve quests")


@router.get("/quests/{quest_id}", response_model=Quest)
async def get_quest(
    quest_id: str,
    _: str = Depends(require_auth)
) -> Quest:
    """Get quest details"""
    quest = await db_client.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    return quest