"""
Application configuration settings.

This module serves as the single source of truth for all application-level
configuration values, particularly those related to the game economy and
business logic. Using Pydantic BaseSettings allows for easy environment
variable overrides while maintaining type safety.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # User Economy Settings
    initial_quest_creation_points: int = Field(
        default=10,
        description="Number of quest creation points new users start with",
        env="INITIAL_QUEST_CREATION_POINTS"
    )
    
    # Quest Economy Settings  
    quest_creation_cost: int = Field(
        default=1,
        description="Number of points required to create a quest",
        env="QUEST_CREATION_COST"
    )
    
    # Quest Rewards (for future use)
    default_quest_xp_reward: int = Field(
        default=100,
        description="Default XP reward for completing a quest",
        env="DEFAULT_QUEST_XP_REWARD"
    )
    
    default_quest_reputation_reward: int = Field(
        default=10,
        description="Default reputation reward for completing a quest",
        env="DEFAULT_QUEST_REPUTATION_REWARD"
    )
    
    # Anti-spam Settings
    max_quests_per_user_per_day: Optional[int] = Field(
        default=None,
        description="Maximum number of quests a user can create per day (None = unlimited)",
        env="MAX_QUESTS_PER_USER_PER_DAY"
    )
    
    # Points Regeneration (for future implementation)
    quest_points_regeneration_rate: int = Field(
        default=0,
        description="Number of quest creation points regenerated per day (0 = no regeneration)",
        env="QUEST_POINTS_REGENERATION_RATE"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # env_prefix="CIVICFORGE_"  # Optional: add prefix to all env vars
    )


# Create a singleton instance
settings = Settings()


# Export specific values for backward compatibility if needed
INITIAL_QUEST_CREATION_POINTS = settings.initial_quest_creation_points
QUEST_CREATION_COST = settings.quest_creation_cost