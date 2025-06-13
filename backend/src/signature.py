"""
Cryptographic signature verification for attestations
"""

from eth_account import Account
from eth_account.messages import encode_defunct
from typing import Optional


def create_attestation_message(quest_id: str, user_id: str, role: str) -> str:
    """
    Create a standardized message for attestation signing.
    This ensures consistency between frontend and backend.
    
    IMPORTANT: This exact format must be used by both frontend and backend.
    Any changes here must be reflected in the frontend component.
    """
    return (
        f"I am attesting to the completion of CivicForge Quest.\n"
        f"Quest ID: {quest_id}\n"
        f"My User ID: {user_id}\n"
        f"My Role: {role}"
    )


def verify_attestation_signature(
    quest_id: str,
    user_id: str,
    role: str,
    signature: str,
    expected_address: str
) -> bool:
    """
    Verify that an attestation signature is valid and from the expected address.
    
    Args:
        quest_id: The quest being attested
        user_id: The user ID making the attestation
        role: The role of the attester (requestor/performer)
        signature: The hex signature string
        expected_address: The expected Ethereum address
        
    Returns:
        True if signature is valid and from expected address, False otherwise
    """
    try:
        # Create the message that should have been signed
        message = create_attestation_message(quest_id, user_id, role)
        
        # Encode the message in the Ethereum format
        encoded_message = encode_defunct(text=message)
        
        # Recover the address from the signature
        recovered_address = Account.recover_message(encoded_message, signature=signature)
        
        # Compare addresses (case-insensitive)
        return recovered_address.lower() == expected_address.lower()
        
    except Exception as e:
        print(f"Error verifying signature: {e}")
        return False


def extract_address_from_signature(
    quest_id: str,
    user_id: str,
    role: str,
    signature: str
) -> Optional[str]:
    """
    Extract the Ethereum address from a signature.
    
    Returns:
        The recovered Ethereum address, or None if recovery fails
    """
    try:
        message = create_attestation_message(quest_id, user_id, role)
        encoded_message = encode_defunct(text=message)
        recovered_address = Account.recover_message(encoded_message, signature=signature)
        return recovered_address
    except Exception as e:
        print(f"Error extracting address from signature: {e}")
        return None