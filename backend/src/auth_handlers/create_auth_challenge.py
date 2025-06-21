"""
Create Auth Challenge Lambda Trigger
Generates and sends email passcode for authentication
"""

import json
import logging
import os
import secrets
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any
from botocore.exceptions import ClientError

# Add rate limiting import
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils.rate_limiter import check_email_rate_limit

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ses_client = boto3.client("ses", region_name=os.environ.get("AWS_REGION", "us-east-1"))
dynamodb = boto3.resource("dynamodb")

# Configuration
PASSCODE_LENGTH = 6
PASSCODE_EXPIRY_MINUTES = 5
PASSCODES_TABLE_NAME = os.environ.get("PASSCODES_TABLE", "civicforge-passcodes")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "login@civicforge.org")
APP_NAME = "CivicForge"


def generate_passcode() -> str:
    """Generate a secure random passcode"""
    return "".join(secrets.choice("0123456789") for _ in range(PASSCODE_LENGTH))


def store_passcode(email: str, passcode: str, table) -> None:
    """Store passcode in DynamoDB with expiration"""
    expiry_time = datetime.utcnow() + timedelta(minutes=PASSCODE_EXPIRY_MINUTES)
    
    table.put_item(
        Item={
            "email": email,
            "passcode": passcode,
            "attempts": 0,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expiry_time.isoformat(),
            "ttl": int(expiry_time.timestamp())  # DynamoDB TTL
        }
    )


def send_passcode_email(email: str, passcode: str) -> bool:
    """Send passcode via email using SES"""
    subject = f"Your {APP_NAME} verification code"
    
    # HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your verification code</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 30px;
                text-align: center;
            }}
            .code {{
                font-size: 32px;
                font-weight: bold;
                letter-spacing: 8px;
                color: #007bff;
                background-color: #fff;
                padding: 15px 25px;
                border-radius: 8px;
                display: inline-block;
                margin: 20px 0;
                border: 2px solid #e9ecef;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 14px;
                color: #6c757d;
            }}
            .warning {{
                color: #dc3545;
                font-size: 14px;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Verify your email</h1>
            <p>Enter this code to sign in to {APP_NAME}:</p>
            <div class="code">{passcode}</div>
            <p>This code expires in {PASSCODE_EXPIRY_MINUTES} minutes.</p>
            <div class="warning">
                If you didn't request this code, you can safely ignore this email.
            </div>
            <div class="footer">
                <p>© {datetime.utcnow().year} {APP_NAME}. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Text fallback
    text_body = f"""
    Your {APP_NAME} verification code
    
    Enter this code to sign in: {passcode}
    
    This code expires in {PASSCODE_EXPIRY_MINUTES} minutes.
    
    If you didn't request this code, you can safely ignore this email.
    
    © {datetime.utcnow().year} {APP_NAME}. All rights reserved.
    """
    
    try:
        response = ses_client.send_email(
            Source=FROM_EMAIL,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"}
                }
            }
        )
        logger.info(f"Email sent successfully. MessageId: {response['MessageId']}")
        return True
    except ClientError as e:
        logger.error(f"Failed to send email: {e}")
        return False


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Create auth challenge Lambda trigger
    
    This function:
    1. Generates a random passcode
    2. Stores it in DynamoDB with expiration
    3. Sends it via email
    4. Returns the challenge metadata
    """
    logger.info(f"Create auth challenge event: {json.dumps(event)}")
    
    # Extract request details
    request = event.get("request", {})
    user_attributes = request.get("userAttributes", {})
    email = user_attributes.get("email", "")
    
    # Initialize response
    response = event.get("response", {})
    
    # Skip passcode generation for social login or passkey authentication
    if request.get("challengeName") != "CUSTOM_CHALLENGE":
        return event
    
    try:
        # Check rate limit before proceeding
        is_allowed, remaining = check_email_rate_limit(email)
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for email: {email}")
            # Return a generic error to avoid information disclosure
            raise Exception("Too many authentication attempts. Please try again later.")
        
        logger.info(f"Rate limit check passed for {email}. Remaining attempts: {remaining}")
        
        # Generate passcode
        passcode = generate_passcode()
        
        # Get DynamoDB table
        table = dynamodb.Table(PASSCODES_TABLE_NAME)
        
        # Store passcode
        store_passcode(email, passcode, table)
        
        # Send email
        email_sent = send_passcode_email(email, passcode)
        
        if not email_sent:
            # If email fails, we must fail the auth challenge
            logger.error(f"Failed to send passcode email to {email}")
            # Clean up the stored passcode
            table.delete_item(Key={"email": email})
            # Raise exception to fail the authentication flow
            raise Exception("Failed to send verification email. Please try again.")
        
        # Set challenge metadata
        response["publicChallengeParameters"] = {
            "email": email,
            "challengeType": "EMAIL_PASSCODE"
        }
        
        # Set private challenge parameters (not sent to client)
        response["privateChallengeParameters"] = {
            "passcode": passcode
        }
        
        # Set challenge metadata for the client
        response["challengeMetadata"] = "EMAIL_PASSCODE"
        
    except Exception as e:
        logger.error(f"Error creating auth challenge: {e}")
        # Don't expose internal errors to client
        response["publicChallengeParameters"] = {
            "error": "CHALLENGE_CREATION_FAILED"
        }
    
    logger.info(f"Create auth challenge response: {json.dumps({k: v for k, v in response.items() if k != 'privateChallengeParameters'})}")
    return event