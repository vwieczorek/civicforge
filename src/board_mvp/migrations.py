"""Database migrations for Board MVP.

Run this script to update an existing database with new fields.
"""

import sqlite3
import os
from datetime import datetime

from . import models

def run_migrations(db_path: str = None):
    """Apply database migrations to add new fields."""
    if db_path is None:
        db_path = os.environ.get("BOARD_DB_PATH", models.DB_PATH)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print(f"Running migrations on {db_path}")
    
    # Check if migrations have already been applied
    cur.execute("PRAGMA table_info(quests)")
    columns = [col[1] for col in cur.fetchall()]
    
    if "category" not in columns:
        print("Adding category field to quests table...")
        cur.execute("ALTER TABLE quests ADD COLUMN category VARCHAR(50)")
    
    if "visibility" not in columns:
        print("Adding visibility field to quests table...")
        cur.execute("ALTER TABLE quests ADD COLUMN visibility VARCHAR(20) DEFAULT 'board'")
    
    if "boost_level" not in columns:
        print("Adding boost_level field to quests table...")
        cur.execute("ALTER TABLE quests ADD COLUMN boost_level INTEGER DEFAULT 0")
    
    # Check experience_ledger for quest_cost_type
    cur.execute("PRAGMA table_info(experience_ledger)")
    exp_columns = [col[1] for col in cur.fetchall()]
    
    if "quest_cost_type" not in exp_columns:
        print("Adding quest_cost_type field to experience_ledger table...")
        # For existing entries, update the entry_type to be more specific
        cur.execute("ALTER TABLE experience_ledger ADD COLUMN quest_cost_type VARCHAR(20)")
    
    # Check users table for authentication fields
    cur.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in cur.fetchall()]
    
    if "email" not in user_columns:
        print("Adding email field to users table...")
        cur.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
    
    if "password_hash" not in user_columns:
        print("Adding password_hash field to users table...")
        cur.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)")
    
    # Create board_config table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS board_config (
            id INTEGER PRIMARY KEY,
            board_id VARCHAR(50) UNIQUE,
            name VARCHAR(100),
            theme TEXT,  -- JSON stored as text
            rules TEXT,  -- JSON stored as text
            xp_rates TEXT,  -- JSON stored as text
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)
    
    # Insert default board config if none exists
    cur.execute("SELECT COUNT(*) FROM board_config")
    if cur.fetchone()[0] == 0:
        print("Creating default board configuration...")
        now = datetime.utcnow().isoformat()
        cur.execute("""
            INSERT INTO board_config (board_id, name, theme, rules, xp_rates, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "board_001",
            "CivicForge Development Board",
            '{"colors": {"primary": "#2563eb", "secondary": "#7c3aed"}}',
            '{"min_reputation_to_verify": 0, "max_quests_per_user": 10}',
            '{"quest_normal": 10, "quest_exceptional": 20, "verify_normal": 5, "verify_exceptional": 10}',
            now,
            now
        ))
    
    conn.commit()
    print("Migrations complete!")
    
    # Show current schema
    print("\nCurrent schema:")
    for table in ["quests", "experience_ledger", "board_config"]:
        print(f"\n{table}:")
        cur.execute(f"PRAGMA table_info({table})")
        for col in cur.fetchall():
            print(f"  - {col[1]} ({col[2]})")
    
    conn.close()


if __name__ == "__main__":
    run_migrations()