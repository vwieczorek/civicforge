"""Database migrations supporting both SQLite and PostgreSQL."""

import os
from datetime import datetime
from .database import Database, get_db


# PostgreSQL-compatible schema
POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    real_name VARCHAR(100) NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    role VARCHAR(50) NOT NULL,
    reputation INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email VARCHAR(255),
    password_hash VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS quests (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    reward INTEGER DEFAULT 0,
    creator_id INTEGER NOT NULL REFERENCES users(id),
    performer_id INTEGER REFERENCES users(id),
    verifier_id INTEGER REFERENCES users(id),
    status VARCHAR(50) NOT NULL,
    category VARCHAR(50),
    visibility VARCHAR(20) DEFAULT 'board',
    boost_level INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verifications (
    id SERIAL PRIMARY KEY,
    quest_id INTEGER NOT NULL REFERENCES quests(id),
    verifier_id INTEGER NOT NULL REFERENCES users(id),
    performer_id INTEGER NOT NULL REFERENCES users(id),
    result VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experience_ledger (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount INTEGER NOT NULL,
    entry_type VARCHAR(50) NOT NULL,
    quest_id INTEGER REFERENCES quests(id),
    quest_cost_type VARCHAR(20),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS board_config (
    id SERIAL PRIMARY KEY,
    board_id VARCHAR(50) UNIQUE,
    name VARCHAR(100),
    theme JSONB,
    rules JSONB,
    xp_rates JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_quests_status ON quests(status);
CREATE INDEX IF NOT EXISTS idx_quests_category ON quests(category);
CREATE INDEX IF NOT EXISTS idx_quests_creator ON quests(creator_id);
CREATE INDEX IF NOT EXISTS idx_quests_performer ON quests(performer_id);
CREATE INDEX IF NOT EXISTS idx_experience_user ON experience_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
"""

# SQLite-compatible schema
SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    real_name TEXT NOT NULL,
    verified INTEGER DEFAULT 0,
    role TEXT NOT NULL,
    reputation INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    email TEXT,
    password_hash TEXT
);

CREATE TABLE IF NOT EXISTS quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    reward INTEGER DEFAULT 0,
    creator_id INTEGER NOT NULL,
    performer_id INTEGER,
    verifier_id INTEGER,
    status TEXT NOT NULL,
    category TEXT,
    visibility TEXT DEFAULT 'board',
    boost_level INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(creator_id) REFERENCES users(id),
    FOREIGN KEY(performer_id) REFERENCES users(id),
    FOREIGN KEY(verifier_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quest_id INTEGER NOT NULL,
    verifier_id INTEGER NOT NULL,
    performer_id INTEGER NOT NULL,
    result TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(quest_id) REFERENCES quests(id),
    FOREIGN KEY(verifier_id) REFERENCES users(id),
    FOREIGN KEY(performer_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS experience_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    entry_type TEXT NOT NULL,
    quest_id INTEGER,
    quest_cost_type TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(quest_id) REFERENCES quests(id)
);

CREATE TABLE IF NOT EXISTS board_config (
    id INTEGER PRIMARY KEY,
    board_id VARCHAR(50) UNIQUE,
    name VARCHAR(100),
    theme TEXT,
    rules TEXT,
    xp_rates TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
"""


def run_migrations(db: Database = None):
    """Run database migrations for either SQLite or PostgreSQL."""
    if db is None:
        db = get_db()
    
    print(f"Running migrations on {db.connection_string}")
    
    # Determine database type
    is_postgres = db.connection_string.startswith(('postgresql://', 'postgres://'))
    
    if is_postgres:
        # For PostgreSQL, we can use CREATE TABLE IF NOT EXISTS
        print("Applying PostgreSQL schema...")
        queries = POSTGRES_SCHEMA.strip().split(';')
        for query in queries:
            if query.strip():
                db.execute(query.strip())
        
        # Insert default board config if none exists
        result = db.fetchone("SELECT COUNT(*) as count FROM board_config")
        if result['count'] == 0:
            print("Creating default board configuration...")
            db.execute("""
                INSERT INTO board_config (board_id, name, theme, rules, xp_rates)
                VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
            """, (
                "board_001",
                "CivicForge Development Board",
                '{"colors": {"primary": "#2563eb", "secondary": "#7c3aed"}}',
                '{"min_reputation_to_verify": 0, "max_quests_per_user": 10}',
                '{"quest_normal": 10, "quest_exceptional": 20, "verify_normal": 5, "verify_exceptional": 10}'
            ))
    
    else:
        # For SQLite, check existing schema and add missing columns
        print("Applying SQLite schema...")
        
        # First create all tables if they don't exist
        queries = SQLITE_SCHEMA.strip().split(';')
        for query in queries:
            if query.strip():
                db.execute(query.strip())
        
        # Check for missing columns in existing tables
        # Note: SQLite doesn't have information_schema, so we use PRAGMA
        
        # Check quests table
        columns = db.fetchall("PRAGMA table_info(quests)")
        column_names = [col['name'] for col in columns]
        
        if "category" not in column_names:
            print("Adding category field to quests table...")
            db.execute("ALTER TABLE quests ADD COLUMN category VARCHAR(50)")
        
        if "visibility" not in column_names:
            print("Adding visibility field to quests table...")
            db.execute("ALTER TABLE quests ADD COLUMN visibility VARCHAR(20) DEFAULT 'board'")
        
        if "boost_level" not in column_names:
            print("Adding boost_level field to quests table...")
            db.execute("ALTER TABLE quests ADD COLUMN boost_level INTEGER DEFAULT 0")
        
        # Check experience_ledger
        columns = db.fetchall("PRAGMA table_info(experience_ledger)")
        column_names = [col['name'] for col in columns]
        
        if "quest_cost_type" not in column_names:
            print("Adding quest_cost_type field to experience_ledger table...")
            db.execute("ALTER TABLE experience_ledger ADD COLUMN quest_cost_type VARCHAR(20)")
        
        # Check users table
        columns = db.fetchall("PRAGMA table_info(users)")
        column_names = [col['name'] for col in columns]
        
        if "email" not in column_names:
            print("Adding email field to users table...")
            db.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
        
        if "password_hash" not in column_names:
            print("Adding password_hash field to users table...")
            db.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)")
        
        # Insert default board config if none exists
        result = db.fetchone("SELECT COUNT(*) as count FROM board_config")
        if result['count'] == 0:
            print("Creating default board configuration...")
            now = datetime.utcnow().isoformat()
            db.execute("""
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
    
    db.commit()
    
    # Create default users after schema is ready
    try:
        from .auth import hash_password
        
        # Check if admin user exists
        admin_exists = db.fetchone("SELECT id FROM users WHERE username=%s", ("admin",))
        if not admin_exists:
            print("Creating default admin user...")
            admin_hash = hash_password("admin123")
            db.execute("""
                INSERT INTO users (username, email, password_hash, real_name, role, reputation, verified)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, ("admin", "admin@civicforge.org", admin_hash, "CivicForge Admin", "Organizer", 20, True))
            db.commit()
        
        # Check if dev user exists
        dev_exists = db.fetchone("SELECT id FROM users WHERE username=%s", ("dev",))
        if not dev_exists:
            print("Creating default dev user...")
            dev_hash = hash_password("dev123")
            db.execute("""
                INSERT INTO users (username, email, password_hash, real_name, role, reputation, verified)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, ("dev", "dev@civicforge.org", dev_hash, "Core Developer", "Participant", 0, False))
            db.commit()
    except Exception as e:
        print(f"Warning: Could not create default users: {e}")
    
    print("Migrations complete!")
    
    # Show current schema summary
    print("\nDatabase initialized with tables:")
    tables = ['users', 'quests', 'verifications', 'experience_ledger', 'board_config']
    for table in tables:
        if is_postgres:
            result = db.fetchone(
                "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_name = %s",
                (table,)
            )
        else:
            result = db.fetchone(
                "SELECT COUNT(*) as count FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
        if result['count'] > 0:
            print(f"  ✓ {table}")
        else:
            print(f"  ✗ {table} (missing)")
    
    db.close()


if __name__ == "__main__":
    # Initialize database from environment
    db = Database()
    run_migrations(db)