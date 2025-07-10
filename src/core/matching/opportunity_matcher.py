"""
Opportunity Matcher for CivicForge

Matches volunteers with civic engagement opportunities based on
skills, availability, location, and preferences.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum

from ..nlp.nlp_processor import NLPResult
from ..interfaces import PrivacyManager, MockPrivacyManager


class MatchConfidence(Enum):
    """Confidence levels for matches"""
    HIGH = "high"  # 80%+ match
    MEDIUM = "medium"  # 60-79% match
    LOW = "low"  # 40-59% match
    POOR = "poor"  # Below 40%


@dataclass
class Opportunity:
    """Represents a civic engagement opportunity"""
    id: str
    title: str
    description: str
    organization: str
    skills_needed: List[str]
    location: str
    time_commitment: Dict[str, str]  # {"day": "saturday", "period": "morning"}
    created_at: datetime
    active: bool = True
    min_volunteers: int = 1
    max_volunteers: Optional[int] = None
    

@dataclass
class VolunteerProfile:
    """Represents a volunteer's preferences and abilities"""
    user_id: str
    skills: List[str]
    interests: List[str]
    availability: List[Dict[str, str]]  # [{"day": "saturday", "period": "morning"}]
    preferred_locations: List[str]
    max_distance_km: Optional[float] = None
    

@dataclass
class Match:
    """Represents a match between volunteer and opportunity"""
    volunteer_id: str
    opportunity_id: str
    confidence: MatchConfidence
    score: float  # 0.0 to 1.0
    matching_factors: Dict[str, float]  # Breakdown of match score
    suggested_reason: str
    

class OpportunityMatcher:
    """Matches volunteers with opportunities"""
    
    def __init__(self, privacy_manager: PrivacyManager = None):
        self.privacy_manager = privacy_manager or MockPrivacyManager()
        
        # Skill synonyms for better matching
        self.skill_synonyms = {
            "teaching": ["education", "tutoring", "mentoring", "instruction"],
            "gardening": ["farming", "agriculture", "planting", "landscaping"],
            "cooking": ["food preparation", "culinary", "meal prep", "kitchen"],
            "technology": ["IT", "computers", "programming", "tech support"],
            "elderly care": ["senior care", "elder support", "aging assistance"],
            "childcare": ["youth work", "kids activities", "child supervision"],
            "construction": ["building", "carpentry", "renovation", "repair"],
            "fundraising": ["donation", "grant writing", "sponsorship"],
            "event planning": ["organizing", "coordination", "event management"],
            "transportation": ["driving", "delivery", "transport assistance"]
        }
        
    def find_matches(self, 
                    volunteer: VolunteerProfile, 
                    opportunities: List[Opportunity],
                    min_confidence: MatchConfidence = MatchConfidence.LOW) -> List[Match]:
        """Find matching opportunities for a volunteer"""
        matches = []
        
        for opportunity in opportunities:
            if not opportunity.active:
                continue
                
            # Calculate match score
            score, factors = self._calculate_match_score(volunteer, opportunity)
            confidence = self._score_to_confidence(score)
            
            # Only include matches above minimum confidence
            if self._confidence_value(confidence) >= self._confidence_value(min_confidence):
                match = Match(
                    volunteer_id=volunteer.user_id,
                    opportunity_id=opportunity.id,
                    confidence=confidence,
                    score=score,
                    matching_factors=factors,
                    suggested_reason=self._generate_match_reason(opportunity, factors)
                )
                matches.append(match)
        
        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)
        
        # Apply privacy filtering
        return self._apply_privacy_limits(matches, volunteer.user_id)
    
    def _calculate_match_score(self, 
                             volunteer: VolunteerProfile,
                             opportunity: Opportunity) -> Tuple[float, Dict[str, float]]:
        """Calculate how well a volunteer matches an opportunity"""
        factors = {}
        
        # Skill matching (40% weight)
        skill_score = self._calculate_skill_match(
            volunteer.skills + volunteer.interests,
            opportunity.skills_needed
        )
        factors["skills"] = skill_score
        
        # Availability matching (30% weight)
        availability_score = self._calculate_availability_match(
            volunteer.availability,
            opportunity.time_commitment
        )
        factors["availability"] = availability_score
        
        # Location matching (20% weight)
        location_score = self._calculate_location_match(
            volunteer.preferred_locations,
            opportunity.location,
            volunteer.max_distance_km
        )
        factors["location"] = location_score
        
        # Interest alignment (10% weight)
        # Check if opportunity description aligns with volunteer interests
        interest_score = self._calculate_interest_alignment(
            volunteer.interests,
            opportunity.description
        )
        factors["interests"] = interest_score
        
        # Calculate weighted total
        total_score = (
            skill_score * 0.4 +
            availability_score * 0.3 +
            location_score * 0.2 +
            interest_score * 0.1
        )
        
        return total_score, factors
    
    def _calculate_skill_match(self, volunteer_skills: List[str], needed_skills: List[str]) -> float:
        """Calculate skill matching score"""
        if not needed_skills:
            return 1.0  # No specific skills needed
            
        if not volunteer_skills:
            return 0.0
            
        # Normalize skills to lowercase
        volunteer_skills_lower = [s.lower() for s in volunteer_skills]
        needed_skills_lower = [s.lower() for s in needed_skills]
        
        matched_skills = 0
        for needed in needed_skills_lower:
            # Direct match
            if needed in volunteer_skills_lower:
                matched_skills += 1
                continue
                
            # Check synonyms
            for skill, synonyms in self.skill_synonyms.items():
                if needed in [skill] + synonyms:
                    for v_skill in volunteer_skills_lower:
                        if v_skill in [skill] + synonyms:
                            matched_skills += 0.8  # Slightly lower score for synonym match
                            break
                    break
        
        return min(matched_skills / len(needed_skills), 1.0)
    
    def _calculate_availability_match(self, 
                                    volunteer_times: List[Dict[str, str]], 
                                    opportunity_time: Dict[str, str]) -> float:
        """Calculate availability matching score"""
        if not opportunity_time:
            return 1.0  # Flexible timing
            
        if not volunteer_times:
            return 0.5  # Unknown availability
        
        # Check for exact match
        for v_time in volunteer_times:
            if (v_time.get("day", "").lower() == opportunity_time.get("day", "").lower() and
                v_time.get("period", "").lower() == opportunity_time.get("period", "").lower()):
                return 1.0
            
            # Partial match (same day, different time)
            if v_time.get("day", "").lower() == opportunity_time.get("day", "").lower():
                return 0.7
                
            # Any day matches
            if v_time.get("day", "").lower() == "any":
                return 0.8
                
        return 0.0
    
    def _calculate_location_match(self,
                                volunteer_locations: List[str],
                                opportunity_location: str,
                                max_distance: Optional[float]) -> float:
        """Calculate location matching score"""
        if not opportunity_location:
            return 1.0  # Remote/flexible location
            
        if not volunteer_locations:
            return 0.5  # Unknown preference
        
        # Normalize locations
        opp_location_lower = opportunity_location.lower()
        volunteer_locations_lower = [loc.lower() for loc in volunteer_locations]
        
        # Check for exact match
        if opp_location_lower in volunteer_locations_lower:
            return 1.0
            
        # Check for partial matches (e.g., "downtown" in "downtown library")
        for v_loc in volunteer_locations_lower:
            if v_loc in opp_location_lower or opp_location_lower in v_loc:
                return 0.8
                
        # If we had real geocoding, we'd calculate distance here
        # For now, return low score for non-matching locations
        return 0.3
    
    def _calculate_interest_alignment(self, interests: List[str], description: str) -> float:
        """Calculate how well interests align with opportunity description"""
        if not interests or not description:
            return 0.5  # Neutral score
            
        description_lower = description.lower()
        matches = 0
        
        for interest in interests:
            if interest.lower() in description_lower:
                matches += 1
                
        if matches == 0:
            return 0.3  # Low but not zero
        elif matches >= 3:
            return 1.0  # Strong alignment
        else:
            return 0.5 + (matches * 0.15)  # Progressive scoring
    
    def _score_to_confidence(self, score: float) -> MatchConfidence:
        """Convert numeric score to confidence level"""
        if score >= 0.8:
            return MatchConfidence.HIGH
        elif score >= 0.6:
            return MatchConfidence.MEDIUM
        elif score >= 0.4:
            return MatchConfidence.LOW
        else:
            return MatchConfidence.POOR
    
    def _confidence_value(self, confidence: MatchConfidence) -> int:
        """Get numeric value for confidence comparison"""
        values = {
            MatchConfidence.HIGH: 4,
            MatchConfidence.MEDIUM: 3,
            MatchConfidence.LOW: 2,
            MatchConfidence.POOR: 1
        }
        return values.get(confidence, 0)
    
    def _generate_match_reason(self, opportunity: Opportunity, factors: Dict[str, float]) -> str:
        """Generate human-readable reason for the match"""
        reasons = []
        
        if factors.get("skills", 0) >= 0.8:
            reasons.append("your skills are a great match")
        elif factors.get("skills", 0) >= 0.5:
            reasons.append("your skills align well")
            
        if factors.get("availability", 0) >= 0.8:
            reasons.append("the timing works perfectly")
        elif factors.get("availability", 0) >= 0.5:
            reasons.append("the schedule could work")
            
        if factors.get("location", 0) >= 0.8:
            reasons.append("it's in your preferred area")
            
        if factors.get("interests", 0) >= 0.7:
            reasons.append("it matches your interests")
        
        if reasons:
            return f"{opportunity.title} because {' and '.join(reasons)}"
        else:
            return f"{opportunity.title} might be worth exploring"
    
    def _apply_privacy_limits(self, matches: List[Match], user_id: str) -> List[Match]:
        """Apply privacy limits to prevent over-profiling"""
        # Check privacy budget
        budget = self.privacy_manager.check_privacy_budget(user_id)
        
        # Limit number of matches shown based on remaining budget
        if budget.queries_used > 80:
            # Near limit - show only top 3
            return matches[:3]
        elif budget.queries_used > 50:
            # Half used - show top 5
            return matches[:5]
        else:
            # Plenty of budget - show up to 10
            return matches[:10]
    
    def create_opportunity_from_nlp(self, nlp_result: NLPResult, organization: str = "Community") -> Optional[Opportunity]:
        """Create an opportunity from NLP-extracted information"""
        if nlp_result.intent.intent != "REQUEST_HELP":
            return None
            
        # Extract time commitment
        time_commitment = {}
        if nlp_result.entities.times:
            time_commitment = nlp_result.entities.times[0]  # Take first time
            
        # Extract location
        location = "Community Center"  # Default
        if nlp_result.entities.locations:
            location = nlp_result.entities.locations[0]
            
        # Generate title from skills/needs
        title = "Community Help Needed"
        if nlp_result.entities.skills:
            title = f"Help Needed: {', '.join(nlp_result.entities.skills[:2])}"
            
        return Opportunity(
            id=f"opp_{datetime.now().timestamp()}",
            title=title,
            description=nlp_result.raw_text,
            organization=organization,
            skills_needed=nlp_result.entities.skills,
            location=location,
            time_commitment=time_commitment,
            created_at=datetime.now()
        )
    
    def create_volunteer_from_nlp(self, nlp_result: NLPResult, user_id: str) -> Optional[VolunteerProfile]:
        """Create a volunteer profile from NLP-extracted information"""
        if nlp_result.intent.intent not in ["OFFER_HELP", "SHARE_SKILLS", "SHARE_AVAILABILITY"]:
            return None
            
        return VolunteerProfile(
            user_id=user_id,
            skills=nlp_result.entities.skills,
            interests=nlp_result.entities.skills,  # Use skills as interests for now
            availability=nlp_result.entities.times,
            preferred_locations=nlp_result.entities.locations
        )