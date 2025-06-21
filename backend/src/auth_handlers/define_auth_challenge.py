"""
Define Auth Challenge Lambda Trigger
Determines the authentication flow for custom email passcode authentication
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Define auth challenge Lambda trigger
    
    This function determines:
    1. Which challenges have been completed
    2. What the next challenge should be
    3. Whether authentication is complete
    """
    logger.info(f"Define auth challenge event: {json.dumps(event)}")
    
    # Extract request details
    request = event.get("request", {})
    session = request.get("session", [])
    
    # Initialize response
    response = event.get("response", {})
    response["issueTokens"] = False
    response["failAuthentication"] = False
    
    # Check if this is a new authentication attempt
    if not session:
        # Start with custom challenge (email passcode)
        response["challengeName"] = "CUSTOM_CHALLENGE"
        return event
    
    # Check the last challenge response
    last_challenge = session[-1] if session else None
    
    if last_challenge:
        challenge_name = last_challenge.get("challengeName")
        challenge_result = last_challenge.get("challengeResult")
        
        # If the last custom challenge was answered correctly, authentication succeeds
        if challenge_name == "CUSTOM_CHALLENGE" and challenge_result is True:
            response["issueTokens"] = True
            response["failAuthentication"] = False
        
        # If the challenge was answered incorrectly
        elif challenge_name == "CUSTOM_CHALLENGE" and challenge_result is False:
            # Check attempt count
            attempt_count = sum(
                1 for s in session 
                if s.get("challengeName") == "CUSTOM_CHALLENGE" 
                and s.get("challengeResult") is False
            )
            
            # Allow up to 3 attempts
            if attempt_count >= 3:
                response["failAuthentication"] = True
            else:
                # Allow another attempt
                response["challengeName"] = "CUSTOM_CHALLENGE"
    
    logger.info(f"Define auth challenge response: {json.dumps(response)}")
    return event