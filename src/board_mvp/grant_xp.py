#!/usr/bin/env python3
"""Grant XP to a user for testing purposes."""

import os
import sys
import psycopg2
from datetime import datetime

def grant_xp_to_user(username, xp_amount):
    """Grant XP to a specific user."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Find user
        cur.execute("SELECT id, username FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        user_id, username = user
        print(f"✅ Found user: {username} (ID: {user_id})")
        
        # Grant XP through experience_ledger
        cur.execute("""
            INSERT INTO experience_ledger (user_id, amount, entry_type, quest_id, timestamp)
            VALUES (%s, %s, %s, NULL, %s)
        """, (user_id, xp_amount, 'testing_grant', datetime.utcnow().isoformat()))
        
        # Update user's XP total
        cur.execute("""
            UPDATE users 
            SET reputation = COALESCE(reputation, 0) + %s 
            WHERE id = %s
        """, (xp_amount, user_id))
        
        # Verify the update
        cur.execute("SELECT reputation FROM users WHERE id = %s", (user_id,))
        new_reputation = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Granted {xp_amount} XP to {username}")
        print(f"   New total XP: {new_reputation}")
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == '__main__':
    # Default to granting 10 XP to admin user
    username = sys.argv[1] if len(sys.argv) > 1 else 'admin'
    xp_amount = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    print(f"🔧 Granting {xp_amount} XP to user '{username}'...")
    
    # Set database URL for AWS RDS
    os.environ['DATABASE_URL'] = 'postgresql://civicforge:gauntlet-hanover-circuit-inspire-ning-waved@civicforge-db.c6n6i0eoyoc9.us-east-1.rds.amazonaws.com:5432/postgres'
    
    success = grant_xp_to_user(username, xp_amount)
    sys.exit(0 if success else 1)