#!/usr/bin/env python3
"""Live demo of CivicForge API - run while server is active"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def demo_health_check():
    """Check API health"""
    print_section("🔍 API Health Check")
    
    response = requests.get(f"{BASE_URL}/health")
    data = response.json()
    
    print(f"✅ Status: {data['status']}")
    print(f"📊 Active sessions: {data['sessions_active']}")
    print(f"🎯 Opportunities: {data['opportunities_count']}")
    print(f"👥 Volunteers: {data['volunteers_count']}")

def demo_volunteer_conversation():
    """Demo a volunteer offering help"""
    print_section("💬 Volunteer Conversation Demo")
    
    # Start conversation
    print("👤 User: Hi! I'd like to volunteer to teach programming to kids")
    conv_data = {"message": "Hi! I'd like to volunteer to teach programming to kids"}
    response = requests.post(f"{BASE_URL}/api/conversation", json=conv_data)
    data = response.json()
    
    print(f"🤖 Bot: {data['response']}")
    session_id = data['session_id']
    
    # Continue conversation
    time.sleep(0.5)
    print("\n👤 User: I'm available Saturday mornings and know Python and Scratch")
    conv_data = {
        "message": "I'm available Saturday mornings and know Python and Scratch",
        "session_id": session_id
    }
    response = requests.post(f"{BASE_URL}/api/conversation", json=conv_data)
    data = response.json()
    
    print(f"🤖 Bot: {data['response']}")
    
    # Add location
    time.sleep(0.5)
    print("\n👤 User: I prefer the downtown community center")
    conv_data = {
        "message": "I prefer the downtown community center",
        "session_id": session_id
    }
    response = requests.post(f"{BASE_URL}/api/conversation", json=conv_data)
    data = response.json()
    
    print(f"🤖 Bot: {data['response']}")
    
    # Show gathered info
    print(f"\n📊 Gathered Information:")
    print(json.dumps(data['gathered_info'], indent=2))
    
    return session_id

def demo_help_request():
    """Demo someone requesting help"""
    print_section("🆘 Help Request Conversation Demo")
    
    # Start conversation
    print("👤 User: We need help setting up a community garden downtown")
    conv_data = {"message": "We need help setting up a community garden downtown"}
    response = requests.post(f"{BASE_URL}/api/conversation", json=conv_data)
    data = response.json()
    
    print(f"🤖 Bot: {data['response']}")
    session_id = data['session_id']
    
    # Add details
    time.sleep(0.5)
    print("\n👤 User: We need people with gardening and landscaping skills")
    conv_data = {
        "message": "We need people with gardening and landscaping skills",
        "session_id": session_id
    }
    response = requests.post(f"{BASE_URL}/api/conversation", json=conv_data)
    data = response.json()
    
    print(f"🤖 Bot: {data['response']}")
    
    # Add timing
    time.sleep(0.5)
    print("\n👤 User: This Saturday afternoon would be perfect, around 2pm")
    conv_data = {
        "message": "This Saturday afternoon would be perfect, around 2pm",
        "session_id": session_id
    }
    response = requests.post(f"{BASE_URL}/api/conversation", json=conv_data)
    data = response.json()
    
    print(f"🤖 Bot: {data['response']}")
    
    # Show gathered info
    print(f"\n📊 Gathered Information:")
    print(json.dumps(data['gathered_info'], indent=2))
    
    return session_id

def demo_create_opportunities():
    """Create some opportunities"""
    print_section("🏛️ Creating Opportunities")
    
    opportunities = [
        {
            "title": "Teach Kids Programming",
            "description": "Help teach Python and Scratch to children ages 8-12",
            "organization": "Code for Kids",
            "skills_needed": ["teaching", "programming", "python", "scratch"],
            "location": "Downtown Community Center",
            "time_commitment": {
                "day": "saturday",
                "period": "morning",
                "duration": "2 hours"
            },
            "min_volunteers": 2,
            "max_volunteers": 5
        },
        {
            "title": "Community Garden Setup",
            "description": "Help create a beautiful community garden in the downtown area",
            "organization": "Green City Initiative",
            "skills_needed": ["gardening", "landscaping", "construction"],
            "location": "Downtown Park",
            "time_commitment": {
                "day": "saturday",
                "period": "afternoon",
                "duration": "4 hours"
            },
            "min_volunteers": 10,
            "max_volunteers": 25
        },
        {
            "title": "Senior Tech Support",
            "description": "Help seniors learn to use smartphones and computers",
            "organization": "Elder Care Network",
            "skills_needed": ["technology", "teaching", "patience"],
            "location": "Senior Center",
            "time_commitment": {
                "day": "sunday",
                "period": "morning",
                "duration": "2 hours"
            },
            "min_volunteers": 3,
            "max_volunteers": 8
        }
    ]
    
    created_ids = []
    for opp in opportunities:
        response = requests.post(f"{BASE_URL}/api/opportunities", json=opp)
        data = response.json()
        created_ids.append(data['id'])
        print(f"✅ Created: {opp['title']} (ID: {data['id']})")
    
    return created_ids

def demo_create_volunteer():
    """Create a volunteer profile"""
    print_section("👤 Creating Volunteer Profile")
    
    volunteer = {
        "user_id": "demo_volunteer_123",
        "skills": ["programming", "teaching", "python", "gardening", "cooking"],
        "interests": ["education", "technology", "environment", "community"],
        "availability": [
            {"day": "saturday", "period": "morning"},
            {"day": "saturday", "period": "afternoon"},
            {"day": "sunday", "period": "morning"}
        ],
        "preferred_locations": ["Downtown", "Community Center", "City Park", "Downtown Community Center"]
    }
    
    response = requests.post(f"{BASE_URL}/api/volunteers", json=volunteer)
    data = response.json()
    
    print(f"✅ Created volunteer profile: {data['user_id']}")
    print(f"\n📋 Profile Details:")
    print(f"  Skills: {', '.join(volunteer['skills'])}")
    print(f"  Interests: {', '.join(volunteer['interests'])}")
    print(f"  Available: {len(volunteer['availability'])} time slots")
    
    return volunteer['user_id']

def demo_matching(volunteer_id):
    """Demo the matching system"""
    print_section("🔍 Finding Matches")
    
    # Try different confidence levels
    for confidence in ["high", "medium", "low"]:
        print(f"\n🎯 Matches with {confidence} confidence:")
        
        match_request = {
            "volunteer_id": volunteer_id,
            "min_confidence": confidence
        }
        
        response = requests.post(f"{BASE_URL}/api/matches", json=match_request)
        data = response.json()
        
        if data['total_matches'] == 0:
            print(f"  No matches found at {confidence} confidence level")
        else:
            for match in data['matches'][:3]:  # Show top 3
                print(f"\n  📌 {match['opportunity']['title']}")
                print(f"     Organization: {match['opportunity']['organization']}")
                print(f"     Location: {match['opportunity']['location']}")
                print(f"     Score: {match['score']:.0%}")
                print(f"     Why: {match['reason']}")

def demo_conversation_to_opportunity(session_id):
    """Convert a conversation to an opportunity"""
    print_section("🔄 Converting Conversation to Opportunity")
    
    # First, confirm the conversation
    print("Confirming the help request conversation...")
    conv_data = {
        "message": "Yes, please create this opportunity",
        "session_id": session_id
    }
    response = requests.post(f"{BASE_URL}/api/conversation", json=conv_data)
    
    # Create opportunity from conversation
    try:
        response = requests.post(f"{BASE_URL}/api/conversation/{session_id}/create_opportunity")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Created opportunity: {data['opportunity']['title']}")
            print(f"   ID: {data['id']}")
            print(f"   Skills needed: {', '.join(data['opportunity']['skills_needed'])}")
        else:
            print(f"❌ Could not create opportunity: {response.json()['detail']}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Run the complete demo"""
    print("🏛️  CivicForge Live API Demo")
    print("=" * 60)
    print("Make sure the API server is running at http://localhost:8000")
    print("=" * 60)
    
    try:
        # Check if server is running
        try:
            requests.get(f"{BASE_URL}/health", timeout=2)
        except:
            print("\n❌ Error: Cannot connect to API server")
            print("Please start the server with:")
            print("  source src/venv/bin/activate")
            print("  PYTHONPATH=$PWD python -m src.api.main")
            return
        
        # Run all demos
        demo_health_check()
        
        # Volunteer conversation
        volunteer_session = demo_volunteer_conversation()
        time.sleep(1)
        
        # Help request conversation
        help_session = demo_help_request()
        time.sleep(1)
        
        # Create opportunities
        opportunity_ids = demo_create_opportunities()
        time.sleep(1)
        
        # Create volunteer
        volunteer_id = demo_create_volunteer()
        time.sleep(1)
        
        # Find matches
        demo_matching(volunteer_id)
        time.sleep(1)
        
        # Convert conversation to opportunity
        demo_conversation_to_opportunity(help_session)
        
        print_section("✅ Demo Complete!")
        print("CivicForge is successfully:")
        print("• Processing natural language conversations")
        print("• Extracting skills, times, and locations")
        print("• Creating opportunities and volunteer profiles")
        print("• Matching volunteers with opportunities")
        print("• Managing multi-turn conversations with state tracking")
        print("\n🚀 The system is ready for you to experiment with!")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()