#!/usr/bin/env python3
"""
Remote Thinker - The AI service component of CivicForge
This is a minimal prototype demonstrating the Remote Thinker concept.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
import random

app = FastAPI(
    title="CivicForge Remote Thinker",
    description="AI service that understands civic needs and discovers opportunities",
    version="0.1.0"
)

# Mock data for demonstration
MOCK_OPPORTUNITIES = [
    {
        "id": "opp-001",
        "title": "Beach Cleanup at Sunset Beach",
        "description": "Help keep our beaches clean and protect marine life",
        "duration": "2 hours",
        "location": "Sunset Beach Park",
        "skills": ["physical_labor", "environmental_awareness"],
        "category": "environment"
    },
    {
        "id": "opp-002",
        "title": "Senior Center Computer Skills Teaching",
        "description": "Teach basic computer skills to seniors",
        "duration": "1.5 hours",
        "location": "Community Senior Center",
        "skills": ["teaching", "patience", "computer_basics"],
        "category": "education"
    },
    {
        "id": "opp-003",
        "title": "Food Bank Distribution Volunteer",
        "description": "Help distribute food to families in need",
        "duration": "3 hours",
        "location": "Central Food Bank",
        "skills": ["organization", "physical_labor", "compassion"],
        "category": "social_services"
    },
    {
        "id": "opp-004",
        "title": "Library Reading Program for Kids",
        "description": "Read stories to children and inspire a love of reading",
        "duration": "1 hour",
        "location": "Public Library",
        "skills": ["reading", "patience", "child_friendly"],
        "category": "education"
    },
    {
        "id": "opp-005",
        "title": "Community Garden Maintenance",
        "description": "Help maintain and expand our community garden",
        "duration": "2 hours",
        "location": "Elm Street Community Garden",
        "skills": ["gardening", "physical_labor"],
        "category": "environment"
    }
]

class CivicQuery(BaseModel):
    """Natural language query from the Local Controller"""
    text: str
    context: Dict[str, Any] = {}
    
class CivicResponse(BaseModel):
    """Response from the Remote Thinker"""
    understood_intent: str
    opportunities: List[Dict[str, Any]]
    suggested_action: str
    conversation_id: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "active",
        "service": "CivicForge Remote Thinker",
        "message": "Ready to help amplify civic engagement"
    }

@app.post("/think", response_model=CivicResponse)
async def think(query: CivicQuery):
    """
    Process natural language queries and discover civic opportunities.
    This is a mock implementation for the prototype.
    """
    
    # Simulate understanding the user's intent
    text_lower = query.text.lower()
    
    # Determine intent based on keywords (simplified for prototype)
    if any(word in text_lower for word in ["help", "volunteer", "contribute", "assist"]):
        intent = "seeking_opportunities"
    elif any(word in text_lower for word in ["free", "available", "time", "hours"]):
        intent = "has_availability"
    elif any(word in text_lower for word in ["teach", "mentor", "guide"]):
        intent = "wants_to_teach"
    elif any(word in text_lower for word in ["environment", "nature", "clean"]):
        intent = "environmental_interest"
    else:
        intent = "general_civic_interest"
    
    # Filter opportunities based on intent (simplified matching)
    relevant_opportunities = []
    
    if "teach" in text_lower or "mentor" in text_lower:
        relevant_opportunities = [opp for opp in MOCK_OPPORTUNITIES 
                                if "teaching" in opp.get("skills", [])]
    elif "environment" in text_lower or "beach" in text_lower or "garden" in text_lower:
        relevant_opportunities = [opp for opp in MOCK_OPPORTUNITIES 
                                if opp["category"] == "environment"]
    elif "senior" in text_lower or "elderly" in text_lower:
        relevant_opportunities = [opp for opp in MOCK_OPPORTUNITIES 
                                if "senior" in opp["title"].lower()]
    else:
        # Return a random selection for general queries
        relevant_opportunities = random.sample(MOCK_OPPORTUNITIES, 
                                            min(3, len(MOCK_OPPORTUNITIES)))
    
    # Generate a conversational response
    if relevant_opportunities:
        suggested_action = f"I found {len(relevant_opportunities)} opportunities that match your interests. Would you like me to tell you more about any of them?"
    else:
        suggested_action = "I'm still learning about opportunities in your area. Could you tell me more about what kind of civic activities interest you?"
    
    return CivicResponse(
        understood_intent=intent,
        opportunities=relevant_opportunities,
        suggested_action=suggested_action,
        conversation_id=f"conv-{datetime.now().timestamp()}"
    )

@app.post("/propose_action")
async def propose_action(opportunity_id: str, user_context: Dict[str, Any] = {}):
    """
    Create a formal action proposal for the Local Controller to approve.
    This demonstrates the approval flow concept.
    """
    
    # Find the opportunity
    opportunity = next((opp for opp in MOCK_OPPORTUNITIES if opp["id"] == opportunity_id), None)
    
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Create an action proposal
    proposal = {
        "id": f"proposal-{datetime.now().timestamp()}",
        "type": "VOLUNTEER_SIGNUP",
        "opportunity": opportunity,
        "proposed_action": f"Sign up for: {opportunity['title']}",
        "requires_approval": True,
        "data_to_share": ["name", "email", "phone"],
        "expires_at": datetime.now().isoformat()
    }
    
    return {
        "proposal": proposal,
        "message": "Please review this proposal in your Local Controller"
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting CivicForge Remote Thinker prototype...")
    print("API documentation will be available at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)