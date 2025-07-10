"""
Tests for Opportunity Matcher
"""

import pytest
from datetime import datetime
from ..opportunity_matcher import (
    OpportunityMatcher,
    Opportunity,
    VolunteerProfile,
    Match,
    MatchConfidence
)


@pytest.fixture
def matcher():
    """Create an OpportunityMatcher instance"""
    return OpportunityMatcher()


@pytest.fixture
def sample_opportunities():
    """Create sample opportunities for testing"""
    return [
        Opportunity(
            id="opp1",
            title="Teaching Assistant",
            description="Help teach programming to kids",
            organization="Code Club",
            skills_needed=["teaching", "programming"],
            location="Downtown Library",
            time_commitment={"day": "saturday", "period": "morning"},
            created_at=datetime.now()
        ),
        Opportunity(
            id="opp2",
            title="Garden Volunteer",
            description="Help maintain community garden",
            organization="Green Thumbs",
            skills_needed=["gardening", "physical work"],
            location="Riverside Park",
            time_commitment={"day": "sunday", "period": "morning"},
            created_at=datetime.now()
        ),
        Opportunity(
            id="opp3",
            title="Senior Tech Support",
            description="Help seniors with technology",
            organization="Senior Center",
            skills_needed=["technology", "teaching", "patience"],
            location="Oak Street Center",
            time_commitment={"day": "wednesday", "period": "afternoon"},
            created_at=datetime.now()
        )
    ]


@pytest.fixture
def sample_volunteer():
    """Create a sample volunteer profile"""
    return VolunteerProfile(
        user_id="volunteer1",
        skills=["teaching", "programming", "technology"],
        interests=["education", "youth work"],
        availability=[
            {"day": "saturday", "period": "morning"},
            {"day": "wednesday", "period": "afternoon"}
        ],
        preferred_locations=["downtown", "library"]
    )


def test_find_matches_high_confidence(matcher, sample_opportunities, sample_volunteer):
    """Test finding high confidence matches"""
    matches = matcher.find_matches(
        sample_volunteer,
        sample_opportunities,
        MatchConfidence.HIGH
    )
    
    # Should match the teaching assistant opportunity with high confidence
    assert len(matches) >= 1
    assert matches[0].opportunity_id == "opp1"
    assert matches[0].confidence == MatchConfidence.HIGH
    assert matches[0].score >= 0.8


def test_find_matches_all_confidence_levels(matcher, sample_opportunities, sample_volunteer):
    """Test finding matches at all confidence levels"""
    matches = matcher.find_matches(
        sample_volunteer,
        sample_opportunities,
        MatchConfidence.LOW
    )
    
    # Should return multiple matches
    assert len(matches) >= 2
    
    # Check matches are sorted by score
    scores = [m.score for m in matches]
    assert scores == sorted(scores, reverse=True)


def test_skill_matching_exact(matcher):
    """Test exact skill matching"""
    score = matcher._calculate_skill_match(
        ["teaching", "programming"],
        ["teaching", "programming"]
    )
    assert score == 1.0


def test_skill_matching_partial(matcher):
    """Test partial skill matching"""
    score = matcher._calculate_skill_match(
        ["teaching", "programming", "music"],
        ["teaching", "programming"]
    )
    assert score == 1.0  # Has all required skills


def test_skill_matching_synonym(matcher):
    """Test skill matching with synonyms"""
    score = matcher._calculate_skill_match(
        ["education", "coding"],  # synonyms
        ["teaching", "programming"]
    )
    assert score > 0.5  # Should match via synonyms


def test_skill_matching_no_match(matcher):
    """Test skill matching with no matches"""
    score = matcher._calculate_skill_match(
        ["cooking", "driving"],
        ["teaching", "programming"]
    )
    assert score == 0.0


def test_availability_exact_match(matcher):
    """Test exact availability matching"""
    score = matcher._calculate_availability_match(
        [{"day": "saturday", "period": "morning"}],
        {"day": "saturday", "period": "morning"}
    )
    assert score == 1.0


def test_availability_partial_match(matcher):
    """Test partial availability matching (same day, different time)"""
    score = matcher._calculate_availability_match(
        [{"day": "saturday", "period": "afternoon"}],
        {"day": "saturday", "period": "morning"}
    )
    assert score == 0.7


def test_availability_any_day(matcher):
    """Test availability matching with 'any' day"""
    score = matcher._calculate_availability_match(
        [{"day": "any", "period": "morning"}],
        {"day": "saturday", "period": "morning"}
    )
    assert score == 0.8


def test_location_exact_match(matcher):
    """Test exact location matching"""
    score = matcher._calculate_location_match(
        ["Downtown Library"],
        "Downtown Library",
        None
    )
    assert score == 1.0


def test_location_partial_match(matcher):
    """Test partial location matching"""
    score = matcher._calculate_location_match(
        ["downtown"],
        "Downtown Library",
        None
    )
    assert score == 0.8


def test_create_opportunity_from_nlp(matcher):
    """Test creating opportunity from NLP result"""
    from ...nlp.nlp_processor import NLPResult
    from ...nlp.intent_recognition import IntentResult
    from ...nlp.entity_extraction import ExtractedEntities
    
    nlp_result = NLPResult(
        intent=IntentResult("REQUEST_HELP", 0.9),
        entities=ExtractedEntities(
            skills=["gardening", "composting"],
            times=[{"day": "saturday", "period": "afternoon"}],
            locations=["community garden"]
        ),
        raw_text="I need help with my garden on Saturday afternoon"
    )
    
    opportunity = matcher.create_opportunity_from_nlp(nlp_result, "Test Org")
    
    assert opportunity is not None
    assert "gardening" in opportunity.skills_needed
    assert opportunity.location == "community garden"
    assert opportunity.time_commitment["day"] == "saturday"


def test_create_volunteer_from_nlp(matcher):
    """Test creating volunteer profile from NLP result"""
    from ...nlp.nlp_processor import NLPResult
    from ...nlp.intent_recognition import IntentResult
    from ...nlp.entity_extraction import ExtractedEntities
    
    nlp_result = NLPResult(
        intent=IntentResult("OFFER_HELP", 0.9),
        entities=ExtractedEntities(
            skills=["teaching", "math"],
            times=[{"day": "weekend", "period": "any"}],
            locations=["library", "school"]
        ),
        raw_text="I can help teach math on weekends at the library"
    )
    
    volunteer = matcher.create_volunteer_from_nlp(nlp_result, "test_user")
    
    assert volunteer is not None
    assert "teaching" in volunteer.skills
    assert "library" in volunteer.preferred_locations
    assert volunteer.user_id == "test_user"


def test_match_reason_generation(matcher, sample_opportunities):
    """Test generation of human-readable match reasons"""
    volunteer = VolunteerProfile(
        user_id="test",
        skills=["teaching", "programming"],
        interests=["education"],
        availability=[{"day": "saturday", "period": "morning"}],
        preferred_locations=["downtown"]
    )
    
    matches = matcher.find_matches(volunteer, sample_opportunities[:1])
    
    assert len(matches) == 1
    reason = matches[0].suggested_reason
    assert "Teaching Assistant" in reason
    assert "skills" in reason.lower() or "timing" in reason.lower()


def test_privacy_limits(matcher, sample_opportunities):
    """Test privacy budget limiting"""
    # Create a volunteer
    volunteer = VolunteerProfile(
        user_id="privacy_test",
        skills=["teaching"],
        interests=[],
        availability=[],
        preferred_locations=[]
    )
    
    # Mock heavy privacy budget usage
    matcher.privacy_manager._budgets["privacy_test"] = matcher.privacy_manager.check_privacy_budget("privacy_test")
    matcher.privacy_manager._budgets["privacy_test"].queries_used = 85
    
    # Should limit results
    matches = matcher.find_matches(volunteer, sample_opportunities * 10)  # Many opportunities
    assert len(matches) <= 3  # Should limit to 3 when near budget limit


def test_empty_opportunities(matcher, sample_volunteer):
    """Test matching with no opportunities"""
    matches = matcher.find_matches(sample_volunteer, [])
    assert len(matches) == 0


def test_inactive_opportunities_filtered(matcher, sample_volunteer):
    """Test that inactive opportunities are filtered out"""
    opportunities = [
        Opportunity(
            id="inactive",
            title="Old Opportunity",
            description="This is inactive",
            organization="Test",
            skills_needed=["teaching"],
            location="Downtown",
            time_commitment={},
            created_at=datetime.now(),
            active=False  # Inactive
        )
    ]
    
    matches = matcher.find_matches(sample_volunteer, opportunities)
    assert len(matches) == 0