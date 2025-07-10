"""
Tests for Skill Analyzer
"""

import pytest
from ..skill_analyzer import SkillAnalyzer, SkillCategory, SkillProfile


@pytest.fixture
def analyzer():
    """Create a SkillAnalyzer instance"""
    return SkillAnalyzer()


def test_analyze_single_skill_exact_match(analyzer):
    """Test analyzing a skill that exactly matches a known skill"""
    profile = analyzer.analyze_skill("teaching")
    
    assert profile.raw_skill == "teaching"
    assert profile.normalized_skill == "teaching"
    assert profile.category == SkillCategory.EDUCATION
    assert "tutoring" in profile.related_skills
    assert "mentoring" in profile.related_skills


def test_analyze_skill_with_proficiency(analyzer):
    """Test analyzing a skill with proficiency indicator"""
    profile = analyzer.analyze_skill("expert programming")
    
    assert profile.proficiency_indicator == "expert"
    assert profile.normalized_skill == "programming"
    assert profile.category == SkillCategory.TECHNOLOGY


def test_analyze_skill_normalization(analyzer):
    """Test skill normalization"""
    profile = analyzer.analyze_skill("IT Skills")
    
    assert profile.normalized_skill == "information technology"
    assert profile.category == SkillCategory.TECHNOLOGY


def test_analyze_skill_category_detection(analyzer):
    """Test correct category detection for various skills"""
    test_cases = [
        ("gardening", SkillCategory.MANUAL_LABOR),
        ("nursing", SkillCategory.HEALTHCARE),
        ("fundraising", SkillCategory.FUNDRAISING),
        ("driving", SkillCategory.TRANSPORTATION),
        ("cooking", SkillCategory.FOOD_SERVICE),
        ("music", SkillCategory.ARTS_CULTURE),
        ("unknown_skill", SkillCategory.GENERAL)
    ]
    
    for skill, expected_category in test_cases:
        profile = analyzer.analyze_skill(skill)
        assert profile.category == expected_category


def test_analyze_skill_set(analyzer):
    """Test analyzing a complete skill set"""
    skills = ["teaching", "programming", "gardening", "cooking"]
    
    result = analyzer.analyze_skill_set(skills)
    
    assert result["skill_count"] == 4
    assert result["primary_category"] in [SkillCategory.EDUCATION, SkillCategory.TECHNOLOGY]
    assert len(result["all_categories"]) >= 3  # Should have multiple categories
    assert result["diversity_score"] > 0.2  # Should show diversity
    assert len(result["suggested_related"]) > 0  # Should suggest related skills


def test_skill_similarity_exact_match(analyzer):
    """Test skill similarity calculation for exact matches"""
    similarity = analyzer.calculate_skill_similarity("teaching", "teaching")
    assert similarity == 1.0


def test_skill_similarity_contains(analyzer):
    """Test skill similarity when one skill contains another"""
    similarity = analyzer.calculate_skill_similarity("teaching", "teaching assistant")
    assert similarity == 0.8


def test_skill_similarity_same_category(analyzer):
    """Test skill similarity for skills in same category"""
    similarity = analyzer.calculate_skill_similarity("teaching", "tutoring")
    assert similarity >= 0.6


def test_skill_similarity_related(analyzer):
    """Test skill similarity for related skills"""
    similarity = analyzer.calculate_skill_similarity("programming", "coding")
    assert similarity >= 0.7  # Should be high due to relationship


def test_skill_similarity_unrelated(analyzer):
    """Test skill similarity for unrelated skills"""
    similarity = analyzer.calculate_skill_similarity("cooking", "programming")
    assert similarity == 0.0


def test_suggest_skills_for_opportunity(analyzer):
    """Test suggesting skills based on opportunity description"""
    description = "Help teach computer programming to youth at the library"
    
    suggestions = analyzer.suggest_skills_for_opportunity(description)
    
    assert "programming" in suggestions
    assert "teaching" in suggestions or "education" in suggestions
    assert len(suggestions) <= 10


def test_get_skill_category_name(analyzer):
    """Test getting human-readable category names"""
    name = analyzer.get_skill_category_name(SkillCategory.EDUCATION)
    assert name == "Education & Training"
    
    name = analyzer.get_skill_category_name(SkillCategory.TECHNOLOGY)
    assert name == "Technology & IT"


def test_related_skills_finding(analyzer):
    """Test finding related skills"""
    # Direct relationship
    related = analyzer._find_related_skills("teaching")
    assert "education" in related
    assert "tutoring" in related
    
    # Category-based relationships
    related = analyzer._find_related_skills("unknown_programming_language")
    assert len(related) > 0  # Should find category-based relations


def test_proficiency_detection_levels(analyzer):
    """Test detection of different proficiency levels"""
    test_cases = [
        ("expert chef", "expert"),
        ("experienced teacher", "experienced"),
        ("intermediate Spanish", "intermediate"),
        ("beginner guitar", "beginner"),
        ("just teaching", None)
    ]
    
    for skill_text, expected_proficiency in test_cases:
        proficiency = analyzer._detect_proficiency(skill_text)
        assert proficiency == expected_proficiency


def test_empty_skill_set(analyzer):
    """Test analyzing empty skill set"""
    result = analyzer.analyze_skill_set([])
    
    assert result["skill_count"] == 0
    assert result["diversity_score"] == 0
    assert len(result["suggested_related"]) == 0


def test_skill_abbreviation_expansion(analyzer):
    """Test expansion of common abbreviations"""
    test_cases = [
        ("IT", "information technology"),
        ("HR", "human resources"),
        ("CPR", "cardiopulmonary resuscitation")
    ]
    
    for abbr, expected in test_cases:
        normalized = analyzer._normalize_skill(abbr)
        assert normalized == expected


def test_skill_normalization_edge_cases(analyzer):
    """Test skill normalization with edge cases"""
    # Extra whitespace
    assert analyzer._normalize_skill("  teaching  skills  ") == "teaching"
    
    # Mixed case
    assert analyzer._normalize_skill("PROGRAMMING") == "programming"
    
    # With common suffixes
    assert analyzer._normalize_skill("cooking ability") == "cooking"