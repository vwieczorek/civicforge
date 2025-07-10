"""
Entity Extraction Tests

Test extraction of skills, times, and locations from natural language.
"""

import pytest
from ..entity_extraction import EntityExtractor, ExtractedEntities


class TestSkillExtraction:
    """Test extraction of skills and abilities"""
    
    def test_direct_skill_mentions(self):
        """Extract skills mentioned directly"""
        extractor = EntityExtractor()
        
        test_cases = [
            ("I'm good at teaching", ["teaching"]),
            ("I know how to code", ["coding"]),
            ("I can help with gardening", ["gardening"]),
            ("I love cooking and baking", ["cooking"]),
            ("I have experience with math tutoring", ["math", "teaching"]),
        ]
        
        for text, expected_skills in test_cases:
            result = extractor.extract(text)
            assert sorted(result.skills) == sorted(expected_skills), \
                f"Failed for '{text}': got {result.skills}, expected {expected_skills}"
    
    def test_profession_based_skills(self):
        """Extract skills from profession statements"""
        extractor = EntityExtractor()
        
        test_cases = [
            ("I'm a teacher", ["teaching"]),
            ("I am a programmer", ["coding"]),
            ("I'm a master gardener", ["gardening"]),
            ("I'm a professional chef", ["cooking"]),
        ]
        
        for text, expected_skills in test_cases:
            result = extractor.extract(text)
            assert result.skills == expected_skills
    
    def test_multiple_skills(self):
        """Extract multiple skills from one message"""
        extractor = EntityExtractor()
        
        text = "I'm a teacher who loves gardening and can also help with computer problems"
        result = extractor.extract(text)
        
        assert "teaching" in result.skills
        assert "gardening" in result.skills
        assert "computer" in result.skills
        assert len(result.skills) == 3
    
    def test_skill_variations(self):
        """Recognize different ways to express the same skill"""
        extractor = EntityExtractor()
        
        # Different ways to say "teaching"
        teaching_variations = [
            "I can teach",
            "I do tutoring",
            "I'm good at instruction",
            "I love educating kids",
        ]
        
        for text in teaching_variations:
            result = extractor.extract(text)
            assert "teaching" in result.skills


class TestTimeExtraction:
    """Test extraction of time availability"""
    
    def test_day_and_period(self):
        """Extract specific day and time period"""
        extractor = EntityExtractor()
        
        test_cases = [
            ("I'm free Saturday mornings", [{"day": "saturday", "period": "morning"}]),
            ("Available Tuesday evenings", [{"day": "tuesday", "period": "evening"}]),
            ("I can help Monday afternoons", [{"day": "monday", "period": "afternoon"}]),
            ("Free on Sunday nights", [{"day": "sunday", "period": "evening"}]),
        ]
        
        for text, expected_times in test_cases:
            result = extractor.extract(text)
            assert result.times == expected_times
    
    def test_general_availability(self):
        """Extract general time periods without specific days"""
        extractor = EntityExtractor()
        
        test_cases = [
            ("I'm free on weekends", [{"day": "weekend", "period": "all_day"}]),
            ("Available weekday evenings", [{"day": "weekday", "period": "all_day"}]),
            ("I have mornings available", [{"day": "any", "period": "morning"}]),
            ("Free in the evenings", [{"day": "any", "period": "evening"}]),
        ]
        
        for text, expected_times in test_cases:
            result = extractor.extract(text)
            assert result.times == expected_times
    
    def test_day_abbreviations(self):
        """Recognize abbreviated day names"""
        extractor = EntityExtractor()
        
        test_cases = [
            ("Free Mon mornings", [{"day": "monday", "period": "morning"}]),
            ("Available Sat afternoons", [{"day": "saturday", "period": "afternoon"}]),
            ("Can help Wed evenings", [{"day": "wednesday", "period": "evening"}]),
        ]
        
        for text, expected_times in test_cases:
            result = extractor.extract(text)
            assert result.times == expected_times


class TestLocationExtraction:
    """Test extraction of location information"""
    
    def test_location_types(self):
        """Extract different types of locations"""
        extractor = EntityExtractor()
        
        test_cases = [
            ("I can help at the community center", ["community_center"]),
            ("Meet me at the library", ["library"]),
            ("We need volunteers downtown", ["downtown"]),
            ("Help needed at local food bank", ["food_bank"]),
            ("Activities in the park", ["park"]),
        ]
        
        for text, expected_locations in test_cases:
            result = extractor.extract(text)
            assert result.locations == expected_locations
    
    def test_location_variations(self):
        """Recognize different ways to express same location"""
        extractor = EntityExtractor()
        
        # Different ways to say "community center"
        center_variations = [
            "at the community center",
            "in the rec center",
            "at our recreation center",
        ]
        
        for text in center_variations:
            result = extractor.extract(text)
            assert "community_center" in result.locations
    
    def test_neighborhood_references(self):
        """Extract references to local areas"""
        extractor = EntityExtractor()
        
        neighborhood_refs = [
            "Help needed in my neighborhood",
            "Activities nearby",
            "Projects in my area",
        ]
        
        for text in neighborhood_refs:
            result = extractor.extract(text)
            assert "neighborhood" in result.locations


class TestComplexExtraction:
    """Test extraction from complex, real-world examples"""
    
    def test_full_volunteer_offer(self):
        """Extract all entities from a complete volunteer offer"""
        extractor = EntityExtractor()
        
        text = "I'm a retired teacher available Saturday mornings at the community center. I can help with math tutoring or gardening."
        result = extractor.extract(text)
        
        # Check skills
        assert "teaching" in result.skills
        assert "math" in result.skills
        assert "gardening" in result.skills
        
        # Check times
        assert {"day": "saturday", "period": "morning"} in result.times
        
        # Check locations
        assert "community_center" in result.locations
    
    def test_volunteer_request(self):
        """Extract entities from a help request"""
        extractor = EntityExtractor()
        
        text = "We need volunteers with cooking skills at the food bank on weekday evenings"
        result = extractor.extract(text)
        
        assert "cooking" in result.skills
        assert {"day": "weekday", "period": "all_day"} in result.times
        assert "food_bank" in result.locations
    
    def test_empty_extraction(self):
        """Handle text with no extractable entities"""
        extractor = EntityExtractor()
        
        text = "Hello, how are you?"
        result = extractor.extract(text)
        
        assert result.skills == []
        assert result.times == []
        assert result.locations == []
        assert result.raw_text == text


# Run with: pytest -xvs test_entity_extraction.py