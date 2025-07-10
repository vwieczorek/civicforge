"""
Matching module for CivicForge

Provides functionality for matching volunteers with opportunities
based on skills, availability, location, and preferences.
"""

from .opportunity_matcher import (
    OpportunityMatcher,
    Opportunity,
    VolunteerProfile,
    Match,
    MatchConfidence
)

from .skill_analyzer import (
    SkillAnalyzer,
    SkillCategory,
    SkillProfile
)

__all__ = [
    # Opportunity matching
    "OpportunityMatcher",
    "Opportunity", 
    "VolunteerProfile",
    "Match",
    "MatchConfidence",
    
    # Skill analysis
    "SkillAnalyzer",
    "SkillCategory",
    "SkillProfile"
]