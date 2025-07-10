#!/usr/bin/env python3
"""
API Demo for CivicForge

Demonstrates how to interact with the CivicForge API for:
1. Having a conversation
2. Creating opportunities and volunteers
3. Finding matches
"""

import requests
import json
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"


def print_response(response: Dict[str, Any], title: str = "Response"):
    """Pretty print API response"""
    print(f"\n{'='*50}")
    print(f"{title}")
    print('='*50)
    print(json.dumps(response, indent=2))


def demo_conversation():
    """Demonstrate the conversation API"""
    print("\n" + "="*70)
    print("CONVERSATION DEMO - Volunteer wanting to help")
    print("="*70)
    
    # Start a conversation
    response = requests.post(
        f"{BASE_URL}/api/conversation",
        json={"message": "Hi, I want to help in my community"}
    )
    data = response.json()
    session_id = data["session_id"]
    
    print_response(data, "Initial Response")
    
    # Continue conversation
    messages = [
        "I'm good at teaching and I have experience with computers",
        "I'm available on weekends, especially Saturday mornings",
        "I prefer to work in the downtown area or near the library",
        "Yes, that's correct!"
    ]
    
    for msg in messages:
        response = requests.post(
            f"{BASE_URL}/api/conversation",
            json={
                "message": msg,
                "session_id": session_id
            }
        )
        data = response.json()
        print_response(data, f"Response to: '{msg}'")
    
    # Get conversation summary
    response = requests.get(f"{BASE_URL}/api/conversation/{session_id}/summary")
    print_response(response.json(), "Final Conversation Summary")
    
    # Create volunteer profile from conversation
    response = requests.post(
        f"{BASE_URL}/api/conversation/{session_id}/create_volunteer",
        params={"user_id": "demo_volunteer_1"}
    )
    print_response(response.json(), "Created Volunteer Profile")
    
    return session_id


def demo_help_request():
    """Demonstrate a help request conversation"""
    print("\n" + "="*70)
    print("CONVERSATION DEMO - Someone needing help")
    print("="*70)
    
    response = requests.post(
        f"{BASE_URL}/api/conversation",
        json={"message": "I need help with my garden"}
    )
    data = response.json()
    session_id = data["session_id"]
    
    print_response(data, "Initial Help Request")
    
    # Continue conversation
    messages = [
        "I need someone who knows about planting vegetables and composting",
        "This Saturday afternoon would be perfect",
        "I live near the community center on Oak Street",
        "Yes, that's all correct"
    ]
    
    for msg in messages:
        response = requests.post(
            f"{BASE_URL}/api/conversation",
            json={
                "message": msg,
                "session_id": session_id
            }
        )
        data = response.json()
        print(response.json()["response"])
    
    # Create opportunity from conversation
    response = requests.post(f"{BASE_URL}/api/conversation/{session_id}/create_opportunity")
    print_response(response.json(), "Created Opportunity from Conversation")
    
    return response.json()["id"]


def demo_direct_opportunity_creation():
    """Demonstrate direct opportunity creation"""
    print("\n" + "="*70)
    print("DIRECT OPPORTUNITY CREATION")
    print("="*70)
    
    opportunities = [
        {
            "title": "Youth Coding Workshop Assistant",
            "description": "Help teach basic programming to middle school students",
            "organization": "Community Library",
            "skills_needed": ["teaching", "programming", "youth work"],
            "location": "Downtown Library",
            "time_commitment": {"day": "saturday", "period": "morning"},
            "min_volunteers": 2,
            "max_volunteers": 5
        },
        {
            "title": "Senior Center Technology Help",
            "description": "Assist seniors with smartphones and computers",
            "organization": "Oak Street Senior Center",
            "skills_needed": ["teaching", "technology", "elderly care", "patience"],
            "location": "Oak Street Senior Center",
            "time_commitment": {"day": "wednesday", "period": "afternoon"}
        },
        {
            "title": "Community Garden Maintenance",
            "description": "Help maintain and expand our community vegetable garden",
            "organization": "Green Thumbs Collective",
            "skills_needed": ["gardening", "composting", "physical work"],
            "location": "Riverside Community Garden",
            "time_commitment": {"day": "any", "period": "morning"}
        }
    ]
    
    created_ids = []
    for opp in opportunities:
        response = requests.post(f"{BASE_URL}/api/opportunities", json=opp)
        data = response.json()
        created_ids.append(data["id"])
        print(f"Created: {data['opportunity']['title']} (ID: {data['id']})")
    
    return created_ids


def demo_matching():
    """Demonstrate the matching functionality"""
    print("\n" + "="*70)
    print("MATCHING DEMO")
    print("="*70)
    
    # Find matches for our demo volunteer
    response = requests.post(
        f"{BASE_URL}/api/matches",
        json={
            "volunteer_id": "demo_volunteer_1",
            "min_confidence": "low"
        }
    )
    
    matches = response.json()
    print_response(matches, "Matching Results")
    
    # Show match details
    print("\nMatch Analysis:")
    for match in matches["matches"]:
        print(f"\n- {match['opportunity']['title']}")
        print(f"  Organization: {match['opportunity']['organization']}")
        print(f"  Location: {match['opportunity']['location']}")
        print(f"  Confidence: {match['confidence']} (score: {match['score']})")
        print(f"  Reason: {match['reason']}")


def demo_skill_analysis():
    """Demonstrate skill analysis (via matching)"""
    print("\n" + "="*70)
    print("SKILL-BASED VOLUNTEER PROFILES")
    print("="*70)
    
    # Create volunteers with different skill sets
    volunteers = [
        {
            "user_id": "tech_volunteer",
            "skills": ["programming", "web design", "teaching", "technology"],
            "interests": ["education", "youth development"],
            "availability": [{"day": "saturday", "period": "morning"}],
            "preferred_locations": ["downtown", "library"]
        },
        {
            "user_id": "garden_volunteer",
            "skills": ["gardening", "composting", "landscaping", "organic farming"],
            "interests": ["environment", "sustainability"],
            "availability": [{"day": "any", "period": "morning"}],
            "preferred_locations": ["riverside", "community garden"]
        },
        {
            "user_id": "generalist_volunteer",
            "skills": ["teaching", "organizing", "communication"],
            "interests": ["community service", "helping others"],
            "availability": [
                {"day": "wednesday", "period": "afternoon"},
                {"day": "saturday", "period": "any"}
            ],
            "preferred_locations": ["anywhere in town"]
        }
    ]
    
    for vol in volunteers:
        response = requests.post(f"{BASE_URL}/api/volunteers", json=vol)
        print(f"Created volunteer: {vol['user_id']}")
    
    # Find matches for each volunteer
    for vol in volunteers:
        response = requests.post(
            f"{BASE_URL}/api/matches",
            json={
                "volunteer_id": vol["user_id"],
                "min_confidence": "medium"
            }
        )
        matches = response.json()
        
        print(f"\nMatches for {vol['user_id']}:")
        if matches["matches"]:
            for match in matches["matches"]:
                print(f"  - {match['opportunity']['title']} ({match['confidence']})")
        else:
            print("  No high-confidence matches found")


def main():
    """Run all demos"""
    print("CivicForge API Demo")
    print("==================")
    print("\nMake sure the API is running at http://localhost:8000")
    print("Run with: python src/run_api.py")
    
    try:
        # Check if API is running
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        print("\n✓ API is running!")
        
        # Run demos
        demo_conversation()
        opportunity_id = demo_help_request()
        demo_direct_opportunity_creation()
        demo_matching()
        demo_skill_analysis()
        
        print("\n" + "="*70)
        print("DEMO COMPLETE!")
        print("="*70)
        print("\nYou can explore the API further at:")
        print(f"- Interactive docs: {BASE_URL}/docs")
        print(f"- Health check: {BASE_URL}/health")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API")
        print("Please make sure the API is running with: python src/run_api.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()