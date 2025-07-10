"""
Entity Extraction for CivicForge

Extracts structured information from natural language input:
- Skills (what people can do)
- Time availability (when people are free)
- Locations (where activities happen)

Following the "start simple" philosophy with pattern-based extraction.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
import re
from datetime import datetime

# Import config loader for externalized patterns
from ..config.config_loader import get_config_loader


@dataclass
class ExtractedEntities:
    """Container for extracted entities from user input"""
    
    skills: List[str] = field(default_factory=list)
    times: List[Dict[str, str]] = field(default_factory=list)  # {"day": "saturday", "period": "morning"}
    locations: List[str] = field(default_factory=list)
    raw_text: str = ""
    

class EntityExtractor:
    """Extracts entities from natural language text"""
    
    def __init__(self, config_loader=None):
        # Use provided config loader or get the singleton
        self.config_loader = config_loader or get_config_loader()
        
        # Load patterns from configuration
        self._load_patterns()
        
    def extract(self, text: str) -> ExtractedEntities:
        """Extract all entities from input text"""
        # Normalize text but preserve original
        text_lower = text.lower().strip()
        
        entities = ExtractedEntities(raw_text=text)
        
        # Extract each entity type
        entities.skills = self._extract_skills(text_lower)
        entities.times = self._extract_times(text_lower)
        entities.locations = self._extract_locations(text_lower)
        
        return entities
        
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills mentioned in text"""
        found_skills = set()
        
        # Look for skill patterns
        for skill_name, patterns in self.skill_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    found_skills.add(skill_name)
                    break
                    
        # Also look for "I'm a/an [profession]" patterns
        profession_patterns = [
            r"i'?m an? (\w+(?:\s+\w+)?)",
            r"i am an? (\w+(?:\s+\w+)?)",
            r"i'?m a (?:professional )?(\w+)",
        ]
        
        for pattern in profession_patterns:
            profession_match = re.search(pattern, text)
            if profession_match:
                profession = profession_match.group(1).lower()
                # Use profession mapping from config
                if profession in self.profession_mapping:
                    found_skills.add(self.profession_mapping[profession])
                
        return sorted(list(found_skills))
        
    def _extract_times(self, text: str) -> List[Dict[str, str]]:
        """Extract time availability from text"""
        found_times = []
        found_combinations = set()  # Track unique combinations
        
        # Look for day + period combinations
        for day_name, day_patterns in self.days_of_week.items():
            for day_pattern in day_patterns:
                if day_pattern in text:
                    # Check if followed by a time period
                    for period_name, period_patterns in self.time_periods.items():
                        for period_pattern in period_patterns:
                            # Look for patterns like "saturday morning" or "morning on saturday"
                            if f"{day_pattern} {period_pattern}" in text or \
                               f"{period_pattern} on {day_pattern}" in text:
                                combo = f"{day_name}_{period_name}"
                                if combo not in found_combinations:
                                    found_combinations.add(combo)
                                    found_times.append({
                                        "day": day_name,
                                        "period": period_name
                                    })
                                break  # Avoid duplicates for same day
                    break  # Found this day, move to next
                                
        # Look for general time periods without specific days
        if not found_times:
            # First check for weekday/weekend with time periods
            weekday_evening = False
            for period_name in ["weekday", "weekend"]:
                if period_name in self.time_periods and any(p in text for p in self.time_periods[period_name]):
                    # Check if it's combined with another time period
                    for other_period, patterns in self.time_periods.items():
                        if other_period not in ["weekday", "weekend"]:
                            for pattern in patterns:
                                if f"{period_name} {pattern}" in text:
                                    found_times.append({
                                        "day": period_name,
                                        "period": "all_day"
                                    })
                                    weekday_evening = True
                                    break
                            if weekday_evening:
                                break
                    
                    # If not combined, just the weekday/weekend itself
                    if not weekday_evening and period_name in text:
                        found_times.append({
                            "day": period_name,
                            "period": "all_day"
                        })
            
            # If still no times found, look for general periods
            if not found_times:
                for period_name, period_patterns in self.time_periods.items():
                    if period_name not in ["weekend", "weekday"]:
                        for period_pattern in period_patterns:
                            if period_pattern in text:
                                found_times.append({
                                    "day": "any",
                                    "period": period_name
                                })
                                break  # Found this period
                            
        return found_times
        
    def _extract_locations(self, text: str) -> List[str]:
        """Extract locations mentioned in text"""
        found_locations = set()
        
        # Look for location type patterns
        for location_type, patterns in self.location_types.items():
            for pattern in patterns:
                if pattern in text:
                    found_locations.add(location_type)
                    break
                    
        # Look for "at/in [location]" patterns
        location_preps = re.findall(r"(?:at|in|near) (?:the )?(\w+(?:\s+\w+)?)", text)
        for loc in location_preps:
            # Map to our location types if possible
            for location_type, patterns in self.location_types.items():
                if any(pattern in loc for pattern in patterns):
                    found_locations.add(location_type)
                    
        return sorted(list(found_locations))
    
    def _load_patterns(self):
        """Load patterns from configuration"""
        # Load skill patterns
        self.skill_patterns = self.config_loader.get_skill_patterns()
        
        # Load time patterns
        time_patterns = self.config_loader.get_time_patterns()
        self.days_of_week = time_patterns["days_of_week"]
        self.time_periods = time_patterns["time_periods"]
        
        # Load location patterns
        self.location_types = self.config_loader.get_location_patterns()
        
        # Load profession mapping
        self.profession_mapping = self.config_loader.get_profession_mapping()
    
    def reload_patterns(self):
        """Reload patterns from configuration (useful for runtime updates)"""
        self.config_loader.reload_entities()
        self._load_patterns()