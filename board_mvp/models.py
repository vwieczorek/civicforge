"""Database models and initialization for the CivicForge Board MVP."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import sqlite3


DB_PATH = "board.db"


@dataclass
class User:
    id: Optional[int]
    username: str
    real_name: str
    verified: bool
    role: str
    reputation: int = 0
    created_at: datetime = datetime.utcnow()


@dataclass
class Quest:
    id: Optional[int]
    title: str
    description: str
    reward: int
    creator_id: int
    performer_id: Optional[int]
    verifier_id: Optional[int]
    status: str
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()


@dataclass
class Verification:
    id: Optional[int]
    quest_id: int
    verifier_id: int
    performer_id: int
    result: str
    created_at: datetime = datetime.utcnow()


@dataclass
class ExperienceEntry:
    id: Optional[int]
    user_id: int
    amount: int
    entry_type: str
    quest_id: Optional[int]
    timestamp: datetime = datetime.utcnow()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    real_name TEXT,
    verified INTEGER DEFAULT 0,
    role TEXT,
    reputation INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
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
    timestamp TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(quest_id) REFERENCES quests(id)
);
"""


def init_db(path: str = DB_PATH) -> sqlite3.Connection:
    """Initialize the SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


if __name__ == "__main__":
    conn = init_db()
    print("Database initialized at", DB_PATH)
    conn.close()
