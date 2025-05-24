import os
import requests
from . import api

"""Seed the board database with initial users and quests for project tracking."""

# Base URL for API calls
API_BASE = "http://localhost:8000/api"


def ensure_user(username: str, email: str, password: str, real_name: str, role: str) -> dict:
    """Create a user if it doesn't already exist, return user info and token."""
    cur = api.get_conn().cursor()
    cur.execute("SELECT id FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    
    if row:
        # User exists, try to login
        print(f"User {username} already exists, attempting login...")
        resp = requests.post(f"{API_BASE}/auth/login", json={
            "username": username,
            "password": password
        })
        if resp.status_code == 200:
            data = resp.json()
            return {"id": data["user_id"], "username": username, "token": data["token"]}
        else:
            print(f"Failed to login as {username}. You may need to delete the database and start fresh.")
            return None
    
    # Register new user
    print(f"Creating user {username}...")
    resp = requests.post(f"{API_BASE}/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
        "real_name": real_name,
        "role": role
    })
    
    if resp.status_code == 200:
        data = resp.json()
        return {"id": data["user_id"], "username": username, "token": data["token"]}
    else:
        print(f"Failed to create user {username}: {resp.json()}")
        return None


def ensure_quest(title: str, description: str, category: str, token: str) -> bool:
    """Create a quest if a matching one does not already exist."""
    # Check if quest exists
    resp = requests.get(f"{API_BASE}/quests")
    if resp.status_code == 200:
        quests = resp.json()
        for quest in quests:
            if quest["title"] == title:
                print(f"Quest '{title}' already exists")
                return True
    
    # Create quest
    print(f"Creating quest: {title}")
    resp = requests.post(
        f"{API_BASE}/quests",
        json={"title": title, "description": description, "category": category},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if resp.status_code == 200:
        return True
    else:
        print(f"Failed to create quest '{title}': {resp.json()}")
        return False


def main():
    print("Seeding the CivicForge Board with initial data...")
    print("Note: The API server must be running on http://localhost:8000")
    print()
    
    # Create initial users
    admin = ensure_user(
        "admin",
        "admin@civicforge.org",
        "admin123",  # Default password for testing
        "CivicForge Admin",
        "Organizer"
    )
    
    if not admin:
        print("Failed to create/login admin user. Exiting.")
        return
    
    dev = ensure_user(
        "dev",
        "dev@civicforge.org",
        "dev123",  # Default password for testing
        "Core Developer",
        "Participant"
    )
    
    if not dev:
        print("Failed to create/login dev user. Exiting.")
        return
    
    print(f"\nAdmin user created with ID {admin['id']} (20 XP granted for Organizers)")
    print(f"Dev user created with ID {dev['id']}")
    
    # Create initial quests using admin's token
    quests = [
        {
            "title": "Implement basic authentication system",
            "description": "Add email/password authentication to protect the Board from unauthorized access.",
            "category": "technical"
        },
        {
            "title": "Migrate project tracking to the Board",
            "description": "Start using the MVP board for tracking development tasks and feedback.",
            "category": "technical"
        },
        {
            "title": "Implement Forge API stubs",
            "description": "Add placeholder endpoints for identity verification and board/feature registration.",
            "category": "technical"
        },
        {
            "title": "Create neighborhood cleanup guide",
            "description": "Write a guide for organizing effective neighborhood cleanup events.",
            "category": "civic"
        },
        {
            "title": "Test quest completion flow",
            "description": "Complete a full quest lifecycle to test the system.",
            "category": "general"
        },
        {
            "title": "Document API endpoints",
            "description": "Create comprehensive documentation for all Board API endpoints.",
            "category": "technical"
        },
        {
            "title": "Add forgot password flow",
            "description": "Implement password reset functionality for users who forget their credentials.",
            "category": "technical"
        },
        {
            "title": "Deploy to AWS",
            "description": "Set up production deployment on AWS with PostgreSQL database.",
            "category": "technical"
        }
    ]
    
    print("\nCreating initial quests...")
    for quest_data in quests:
        ensure_quest(
            quest_data["title"],
            quest_data["description"],
            quest_data["category"],
            admin["token"]
        )
    
    print("\n" + "="*50)
    print("Seeding complete!")
    print("\nDefault credentials:")
    print("  Admin: username='admin', password='admin123'")
    print("  Dev:   username='dev', password='dev123'")
    print("\nYou can now login at http://localhost:8000/login")
    print("="*50)


if __name__ == "__main__":
    main()