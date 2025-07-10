"""
Main API application for CivicForge

Provides endpoints for conversation management and opportunity matching.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import uuid

from ..core.conversation import DialogManager, ConversationState
from ..core.conversation.context_tracker import ContextTracker
from ..core.matching import (
    OpportunityMatcher, 
    Opportunity,
    VolunteerProfile,
    MatchConfidence
)
from ..core.interfaces import MockLocalController, MockPrivacyManager


# Initialize FastAPI app
app = FastAPI(
    title="CivicForge API",
    description="Conversational AI for civic engagement",
    version="0.1.0"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory storage for development (replace with database in production)
sessions = {}
opportunities = {}
volunteers = {}


# Pydantic models for API
class ConversationInput(BaseModel):
    message: str
    session_id: Optional[str] = None


class ConversationResponse(BaseModel):
    response: str
    session_id: str
    state: str
    gathered_info: Dict
    

class OpportunityCreate(BaseModel):
    title: str
    description: str
    organization: str
    skills_needed: List[str]
    location: str
    time_commitment: Dict[str, str]
    min_volunteers: int = 1
    max_volunteers: Optional[int] = None


class VolunteerCreate(BaseModel):
    user_id: str
    skills: List[str]
    interests: List[str]
    availability: List[Dict[str, str]]
    preferred_locations: List[str]
    max_distance_km: Optional[float] = None


class MatchRequest(BaseModel):
    volunteer_id: str
    min_confidence: str = "low"  # "high", "medium", "low"


# Dependency to get or create session
def get_session(session_id: Optional[str] = None) -> Dict:
    if session_id and session_id in sessions:
        return sessions[session_id]
    
    # Create new session
    new_session_id = str(uuid.uuid4())
    dialog_manager = DialogManager(
        context_tracker=ContextTracker(),
        local_controller=MockLocalController(),
        privacy_manager=MockPrivacyManager()
    )
    
    sessions[new_session_id] = {
        "id": new_session_id,
        "dialog_manager": dialog_manager,
        "created_at": datetime.now()
    }
    
    return sessions[new_session_id]


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to CivicForge API",
        "version": "0.1.0",
        "endpoints": {
            "conversation": "/api/conversation",
            "opportunities": "/api/opportunities",
            "volunteers": "/api/volunteers",
            "matches": "/api/matches"
        }
    }


@app.post("/api/conversation", response_model=ConversationResponse)
async def process_conversation(input_data: ConversationInput):
    """Process a conversation turn"""
    session = get_session(input_data.session_id)
    dialog_manager = session["dialog_manager"]
    
    # Process the user input
    response = dialog_manager.process_turn(input_data.message)
    
    # Get conversation summary
    summary = dialog_manager.get_conversation_summary()
    
    return ConversationResponse(
        response=response,
        session_id=session["id"],
        state=summary["state"],
        gathered_info=summary["gathered_info"]
    )


@app.get("/api/conversation/{session_id}/summary")
async def get_conversation_summary(session_id: str):
    """Get summary of a conversation session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    dialog_manager = sessions[session_id]["dialog_manager"]
    return dialog_manager.get_conversation_summary()


@app.post("/api/conversation/{session_id}/reset")
async def reset_conversation(session_id: str):
    """Reset a conversation session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    dialog_manager = sessions[session_id]["dialog_manager"]
    dialog_manager.reset_conversation()
    
    return {"message": "Conversation reset successfully"}


@app.post("/api/opportunities", response_model=Dict)
async def create_opportunity(opportunity: OpportunityCreate):
    """Create a new volunteer opportunity"""
    opp_id = f"opp_{uuid.uuid4()}"
    
    new_opportunity = Opportunity(
        id=opp_id,
        title=opportunity.title,
        description=opportunity.description,
        organization=opportunity.organization,
        skills_needed=opportunity.skills_needed,
        location=opportunity.location,
        time_commitment=opportunity.time_commitment,
        created_at=datetime.now(),
        min_volunteers=opportunity.min_volunteers,
        max_volunteers=opportunity.max_volunteers
    )
    
    opportunities[opp_id] = new_opportunity
    
    return {
        "id": opp_id,
        "message": "Opportunity created successfully",
        "opportunity": {
            "id": new_opportunity.id,
            "title": new_opportunity.title,
            "organization": new_opportunity.organization
        }
    }


@app.get("/api/opportunities")
async def list_opportunities(limit: int = 10, offset: int = 0):
    """List all opportunities"""
    opp_list = list(opportunities.values())
    
    # Sort by created_at descending
    opp_list.sort(key=lambda x: x.created_at, reverse=True)
    
    # Apply pagination
    paginated = opp_list[offset:offset + limit]
    
    return {
        "total": len(opportunities),
        "limit": limit,
        "offset": offset,
        "opportunities": [
            {
                "id": opp.id,
                "title": opp.title,
                "organization": opp.organization,
                "skills_needed": opp.skills_needed,
                "location": opp.location,
                "time_commitment": opp.time_commitment,
                "created_at": opp.created_at.isoformat()
            }
            for opp in paginated
        ]
    }


@app.get("/api/opportunities/{opportunity_id}")
async def get_opportunity(opportunity_id: str):
    """Get a specific opportunity"""
    if opportunity_id not in opportunities:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    opp = opportunities[opportunity_id]
    return {
        "id": opp.id,
        "title": opp.title,
        "description": opp.description,
        "organization": opp.organization,
        "skills_needed": opp.skills_needed,
        "location": opp.location,
        "time_commitment": opp.time_commitment,
        "created_at": opp.created_at.isoformat(),
        "active": opp.active,
        "min_volunteers": opp.min_volunteers,
        "max_volunteers": opp.max_volunteers
    }


@app.post("/api/volunteers", response_model=Dict)
async def create_volunteer(volunteer: VolunteerCreate):
    """Create or update a volunteer profile"""
    volunteer_profile = VolunteerProfile(
        user_id=volunteer.user_id,
        skills=volunteer.skills,
        interests=volunteer.interests,
        availability=volunteer.availability,
        preferred_locations=volunteer.preferred_locations,
        max_distance_km=volunteer.max_distance_km
    )
    
    volunteers[volunteer.user_id] = volunteer_profile
    
    return {
        "user_id": volunteer.user_id,
        "message": "Volunteer profile created/updated successfully"
    }


@app.get("/api/volunteers/{user_id}")
async def get_volunteer(user_id: str):
    """Get a volunteer profile"""
    if user_id not in volunteers:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    
    vol = volunteers[user_id]
    return {
        "user_id": vol.user_id,
        "skills": vol.skills,
        "interests": vol.interests,
        "availability": vol.availability,
        "preferred_locations": vol.preferred_locations,
        "max_distance_km": vol.max_distance_km
    }


@app.post("/api/matches")
async def find_matches(request: MatchRequest):
    """Find matching opportunities for a volunteer"""
    if request.volunteer_id not in volunteers:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    
    volunteer = volunteers[request.volunteer_id]
    
    # Convert string confidence to enum
    confidence_map = {
        "high": MatchConfidence.HIGH,
        "medium": MatchConfidence.MEDIUM,
        "low": MatchConfidence.LOW
    }
    min_confidence = confidence_map.get(request.min_confidence, MatchConfidence.LOW)
    
    # Initialize matcher
    matcher = OpportunityMatcher()
    
    # Find matches
    matches = matcher.find_matches(
        volunteer,
        list(opportunities.values()),
        min_confidence
    )
    
    return {
        "volunteer_id": request.volunteer_id,
        "total_matches": len(matches),
        "matches": [
            {
                "opportunity_id": match.opportunity_id,
                "confidence": match.confidence.value,
                "score": round(match.score, 2),
                "reason": match.suggested_reason,
                "opportunity": {
                    "title": opportunities[match.opportunity_id].title,
                    "organization": opportunities[match.opportunity_id].organization,
                    "location": opportunities[match.opportunity_id].location
                }
            }
            for match in matches
        ]
    }


@app.post("/api/conversation/{session_id}/create_opportunity")
async def create_opportunity_from_conversation(session_id: str):
    """Create an opportunity from conversation data"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    dialog_manager = sessions[session_id]["dialog_manager"]
    summary = dialog_manager.get_conversation_summary()
    
    # Check if we have enough information
    gathered = summary["gathered_info"]
    if not gathered.get("confirmed") or gathered.get("intent") != "REQUEST_HELP":
        raise HTTPException(
            status_code=400, 
            detail="Conversation must be confirmed and be a help request"
        )
    
    # Create opportunity from gathered info
    opp_id = f"opp_{uuid.uuid4()}"
    
    # Build time commitment
    time_commitment = {}
    if gathered.get("times"):
        time_commitment = gathered["times"][0]  # Use first time
    
    new_opportunity = Opportunity(
        id=opp_id,
        title=f"Help Needed: {', '.join(gathered.get('skills', ['General Help'])[:2])}",
        description=f"Community member needs help with: {', '.join(gathered.get('skills', []))}",
        organization="Community Request",
        skills_needed=gathered.get("skills", []),
        location=gathered.get("locations", ["Community Center"])[0],
        time_commitment=time_commitment,
        created_at=datetime.now()
    )
    
    opportunities[opp_id] = new_opportunity
    
    return {
        "id": opp_id,
        "message": "Opportunity created from conversation",
        "opportunity": {
            "id": new_opportunity.id,
            "title": new_opportunity.title,
            "skills_needed": new_opportunity.skills_needed
        }
    }


@app.post("/api/conversation/{session_id}/create_volunteer")
async def create_volunteer_from_conversation(session_id: str, user_id: str):
    """Create a volunteer profile from conversation data"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    dialog_manager = sessions[session_id]["dialog_manager"]
    summary = dialog_manager.get_conversation_summary()
    
    # Check if we have enough information
    gathered = summary["gathered_info"]
    if not gathered.get("confirmed") or gathered.get("intent") not in ["OFFER_HELP", "SHARE_SKILLS"]:
        raise HTTPException(
            status_code=400, 
            detail="Conversation must be confirmed and be a volunteer offer"
        )
    
    # Create volunteer profile from gathered info
    volunteer_profile = VolunteerProfile(
        user_id=user_id,
        skills=gathered.get("skills", []),
        interests=gathered.get("skills", []),  # Use skills as interests
        availability=gathered.get("times", []),
        preferred_locations=gathered.get("locations", [])
    )
    
    volunteers[user_id] = volunteer_profile
    
    return {
        "user_id": user_id,
        "message": "Volunteer profile created from conversation",
        "profile": {
            "skills": volunteer_profile.skills,
            "availability": volunteer_profile.availability,
            "locations": volunteer_profile.preferred_locations
        }
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "sessions_active": len(sessions),
        "opportunities_count": len(opportunities),
        "volunteers_count": len(volunteers)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)