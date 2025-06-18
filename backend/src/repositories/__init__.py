"""Repository pattern implementation for centralized data access."""
from .user_repository import UserRepository
from .quest_repository import QuestRepository
from .failed_reward_repository import FailedRewardRepository
from .base import BaseRepository

__all__ = [
    'BaseRepository',
    'UserRepository',
    'QuestRepository',
    'FailedRewardRepository'
]