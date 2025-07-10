"""
Skill Analyzer for CivicForge

Analyzes and categorizes skills to enable better matching between
volunteers and opportunities. Handles skill normalization, categorization,
and relationship mapping.
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Tuple, Any
from enum import Enum
import re


class SkillCategory(Enum):
    """High-level skill categories for civic engagement"""
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    TECHNOLOGY = "technology"
    MANUAL_LABOR = "manual_labor"
    ARTS_CULTURE = "arts_culture"
    SOCIAL_SERVICES = "social_services"
    ENVIRONMENTAL = "environmental"
    ADMINISTRATIVE = "administrative"
    FUNDRAISING = "fundraising"
    TRANSPORTATION = "transportation"
    FOOD_SERVICE = "food_service"
    GENERAL = "general"


@dataclass
class SkillProfile:
    """Represents analyzed skill information"""
    raw_skill: str
    normalized_skill: str
    category: SkillCategory
    related_skills: List[str]
    proficiency_indicator: Optional[str] = None  # "beginner", "experienced", etc.


class SkillAnalyzer:
    """Analyzes and categorizes civic engagement skills"""
    
    def __init__(self):
        # Initialize skill mappings
        self._init_skill_categories()
        self._init_skill_relationships()
        self._init_proficiency_indicators()
        
    def _init_skill_categories(self):
        """Initialize skill to category mappings"""
        self.skill_categories = {
            SkillCategory.EDUCATION: {
                "teaching", "tutoring", "mentoring", "education", "instruction",
                "coaching", "training", "curriculum", "literacy", "math",
                "science", "homework help", "test prep", "esl", "language"
            },
            SkillCategory.HEALTHCARE: {
                "nursing", "medical", "healthcare", "first aid", "cpr",
                "elderly care", "patient care", "therapy", "counseling",
                "mental health", "wellness", "fitness", "nutrition"
            },
            SkillCategory.TECHNOLOGY: {
                "programming", "coding", "it", "tech support", "computers",
                "software", "web design", "data entry", "digital literacy",
                "social media", "cybersecurity", "networking", "database"
            },
            SkillCategory.MANUAL_LABOR: {
                "construction", "carpentry", "plumbing", "electrical",
                "painting", "repair", "maintenance", "landscaping",
                "gardening", "farming", "cleaning", "moving", "heavy lifting"
            },
            SkillCategory.ARTS_CULTURE: {
                "art", "music", "dance", "theater", "photography", "video",
                "graphic design", "writing", "poetry", "crafts", "museum",
                "cultural", "performance", "creative"
            },
            SkillCategory.SOCIAL_SERVICES: {
                "social work", "case management", "advocacy", "outreach",
                "homeless services", "youth work", "childcare", "foster care",
                "addiction support", "crisis intervention", "community organizing"
            },
            SkillCategory.ENVIRONMENTAL: {
                "environmental", "conservation", "recycling", "sustainability",
                "climate", "clean energy", "wildlife", "ecology", "green",
                "composting", "water quality", "tree planting"
            },
            SkillCategory.ADMINISTRATIVE: {
                "administration", "office", "filing", "scheduling", "reception",
                "data management", "bookkeeping", "accounting", "hr",
                "project management", "coordination", "planning"
            },
            SkillCategory.FUNDRAISING: {
                "fundraising", "grant writing", "donor relations", "events",
                "sponsorship", "crowdfunding", "auction", "campaign",
                "marketing", "pr", "communications", "publicity"
            },
            SkillCategory.TRANSPORTATION: {
                "driving", "delivery", "transportation", "logistics",
                "van driver", "cdl", "moving", "errands", "pickup"
            },
            SkillCategory.FOOD_SERVICE: {
                "cooking", "food prep", "kitchen", "serving", "catering",
                "meal planning", "nutrition", "food safety", "baking",
                "food distribution", "soup kitchen", "food bank"
            }
        }
        
        # Create reverse mapping for quick lookup
        self.skill_to_category = {}
        for category, skills in self.skill_categories.items():
            for skill in skills:
                self.skill_to_category[skill] = category
    
    def _init_skill_relationships(self):
        """Initialize related skills mapping"""
        self.skill_relationships = {
            # Teaching related
            "teaching": ["education", "tutoring", "mentoring", "instruction", "training"],
            "tutoring": ["teaching", "mentoring", "homework help", "education"],
            "mentoring": ["coaching", "guidance", "youth work", "teaching"],
            
            # Healthcare related
            "elderly care": ["senior care", "patient care", "companionship", "healthcare"],
            "nursing": ["medical", "patient care", "healthcare", "first aid"],
            
            # Technology related
            "programming": ["coding", "software", "web design", "it"],
            "it": ["tech support", "computers", "networking", "programming"],
            
            # Manual labor related
            "construction": ["building", "carpentry", "renovation", "repair"],
            "gardening": ["landscaping", "farming", "planting", "yard work"],
            
            # Social services related
            "social work": ["case management", "counseling", "advocacy", "outreach"],
            "childcare": ["youth work", "babysitting", "child development", "education"],
            
            # Administrative related
            "project management": ["coordination", "planning", "organization", "leadership"],
            "data entry": ["typing", "data management", "office work", "administration"]
        }
    
    def _init_proficiency_indicators(self):
        """Initialize proficiency level indicators"""
        self.proficiency_keywords = {
            "expert": ["expert", "professional", "certified", "licensed", "master"],
            "experienced": ["experienced", "skilled", "proficient", "advanced"],
            "intermediate": ["intermediate", "some experience", "familiar"],
            "beginner": ["beginner", "learning", "basic", "entry level", "new to"]
        }
    
    def analyze_skill(self, skill_text: str) -> SkillProfile:
        """Analyze a single skill and return detailed profile"""
        # Normalize the skill text
        normalized = self._normalize_skill(skill_text)
        
        # Detect proficiency level
        proficiency = self._detect_proficiency(skill_text)
        
        # Categorize the skill
        category = self._categorize_skill(normalized)
        
        # Find related skills
        related = self._find_related_skills(normalized)
        
        return SkillProfile(
            raw_skill=skill_text,
            normalized_skill=normalized,
            category=category,
            related_skills=related,
            proficiency_indicator=proficiency
        )
    
    def analyze_skill_set(self, skills: List[str]) -> Dict[str, Any]:
        """Analyze a complete set of skills"""
        analyzed_skills = []
        categories = {}
        all_related = set()
        
        for skill in skills:
            profile = self.analyze_skill(skill)
            analyzed_skills.append(profile)
            
            # Count categories
            if profile.category not in categories:
                categories[profile.category] = 0
            categories[profile.category] += 1
            
            # Collect all related skills
            all_related.update(profile.related_skills)
        
        # Determine primary category
        primary_category = max(categories.items(), key=lambda x: x[1])[0] if categories else SkillCategory.GENERAL
        
        # Calculate diversity score (0-1)
        diversity_score = len(categories) / len(SkillCategory) if analyzed_skills else 0
        
        return {
            "skills": analyzed_skills,
            "primary_category": primary_category,
            "all_categories": list(categories.keys()),
            "category_distribution": categories,
            "suggested_related": list(all_related - set(skills)),
            "diversity_score": diversity_score,
            "skill_count": len(analyzed_skills)
        }
    
    def _normalize_skill(self, skill: str) -> str:
        """Normalize skill text for consistency"""
        # Convert to lowercase
        skill = skill.lower().strip()
        
        # Remove common suffixes/prefixes
        skill = re.sub(r'\b(skills?|ability|experience|knowledge)\b', '', skill)
        
        # Remove extra whitespace
        skill = ' '.join(skill.split())
        
        # Common abbreviation expansions
        abbreviations = {
            "it": "information technology",
            "hr": "human resources",
            "pr": "public relations",
            "esl": "english as second language",
            "cpr": "cardiopulmonary resuscitation",
            "cdl": "commercial drivers license"
        }
        
        for abbr, full in abbreviations.items():
            if skill == abbr:
                skill = full
                
        return skill
    
    def _detect_proficiency(self, skill_text: str) -> Optional[str]:
        """Detect proficiency level from skill description"""
        skill_lower = skill_text.lower()
        
        for level, keywords in self.proficiency_keywords.items():
            for keyword in keywords:
                if keyword in skill_lower:
                    return level
                    
        return None
    
    def _categorize_skill(self, normalized_skill: str) -> SkillCategory:
        """Categorize a normalized skill"""
        # Direct lookup
        if normalized_skill in self.skill_to_category:
            return self.skill_to_category[normalized_skill]
            
        # Check if any category keywords are in the skill
        for category, skills in self.skill_categories.items():
            for skill_keyword in skills:
                if skill_keyword in normalized_skill or normalized_skill in skill_keyword:
                    return category
                    
        # Default to general
        return SkillCategory.GENERAL
    
    def _find_related_skills(self, normalized_skill: str) -> List[str]:
        """Find skills related to the given skill"""
        related = set()
        
        # Direct relationship lookup
        if normalized_skill in self.skill_relationships:
            related.update(self.skill_relationships[normalized_skill])
            
        # Check partial matches
        for skill, relations in self.skill_relationships.items():
            if skill in normalized_skill or normalized_skill in skill:
                related.update(relations)
                
        # Find skills in same category
        category = self._categorize_skill(normalized_skill)
        if category != SkillCategory.GENERAL:
            category_skills = list(self.skill_categories[category])[:5]  # Limit to 5
            related.update(category_skills)
            
        # Remove the original skill
        related.discard(normalized_skill)
        
        return list(related)[:10]  # Return top 10 related skills
    
    def calculate_skill_similarity(self, skill1: str, skill2: str) -> float:
        """Calculate similarity between two skills (0-1)"""
        # Normalize both skills
        norm1 = self._normalize_skill(skill1)
        norm2 = self._normalize_skill(skill2)
        
        # Exact match
        if norm1 == norm2:
            return 1.0
            
        # Check if one contains the other
        if norm1 in norm2 or norm2 in norm1:
            return 0.8
            
        # Check categories
        cat1 = self._categorize_skill(norm1)
        cat2 = self._categorize_skill(norm2)
        
        if cat1 == cat2 and cat1 != SkillCategory.GENERAL:
            return 0.6
            
        # Check related skills
        related1 = set(self._find_related_skills(norm1))
        related2 = set(self._find_related_skills(norm2))
        
        if norm1 in related2 or norm2 in related1:
            return 0.7
            
        # Check overlap in related skills
        overlap = related1.intersection(related2)
        if overlap:
            return 0.4 + (len(overlap) / max(len(related1), len(related2))) * 0.2
            
        return 0.0
    
    def suggest_skills_for_opportunity(self, opportunity_description: str) -> List[str]:
        """Suggest skills that might be needed for an opportunity"""
        description_lower = opportunity_description.lower()
        suggested_skills = set()
        
        # Check each category's keywords
        for category, skills in self.skill_categories.items():
            for skill in skills:
                if skill in description_lower:
                    suggested_skills.add(skill)
                    # Add some related skills too
                    if skill in self.skill_relationships:
                        suggested_skills.update(self.skill_relationships[skill][:2])
                        
        return list(suggested_skills)[:10]  # Return top 10 suggestions
    
    def get_skill_category_name(self, category: SkillCategory) -> str:
        """Get human-readable name for skill category"""
        names = {
            SkillCategory.EDUCATION: "Education & Training",
            SkillCategory.HEALTHCARE: "Healthcare & Wellness",
            SkillCategory.TECHNOLOGY: "Technology & IT",
            SkillCategory.MANUAL_LABOR: "Manual Labor & Trades",
            SkillCategory.ARTS_CULTURE: "Arts & Culture",
            SkillCategory.SOCIAL_SERVICES: "Social Services",
            SkillCategory.ENVIRONMENTAL: "Environmental & Conservation",
            SkillCategory.ADMINISTRATIVE: "Administrative & Office",
            SkillCategory.FUNDRAISING: "Fundraising & Marketing",
            SkillCategory.TRANSPORTATION: "Transportation & Delivery",
            SkillCategory.FOOD_SERVICE: "Food Service & Nutrition",
            SkillCategory.GENERAL: "General & Other"
        }
        return names.get(category, "Other")