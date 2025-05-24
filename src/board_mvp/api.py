from enum import Enum
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

import os
from . import models
from . import auth

app = FastAPI(title="CivicForge Board MVP")

# Initialize database when the module is imported. The path can be overridden
# with the ``BOARD_DB_PATH`` environment variable for testing purposes.
DB_PATH = os.environ.get("BOARD_DB_PATH", models.DB_PATH)

# Create a new connection for each thread
import threading
_thread_local = threading.local()

def get_conn():
    if not hasattr(_thread_local, 'conn'):
        _thread_local.conn = models.init_db(DB_PATH)
    return _thread_local.conn

# For backward compatibility
conn = get_conn()

# Initialize the database structure on first import
models.init_db(DB_PATH)

# Weekly decay amount for experience points
WEEKLY_DECAY = 1

# Experience costs
QUEST_CREATION_COST = 5  # Experience points required to create a quest
QUEST_BOOST_COST = 10    # Experience points to boost/highlight a quest


class UserCreate(BaseModel):
    username: str
    real_name: str
    role: str


class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    real_name: str
    role: str = "Participant"


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    user_id: int
    username: str


class QuestCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    reward: int = 0
    category: Optional[str] = None


class VerificationRequest(BaseModel):
    result: str  # "normal", "exceptional", or "failed"


class QuestStatus(str, Enum):
    OPEN = "S1_OPEN"
    CLAIMED = "S2_CLAIMED"
    WORK_SUBMITTED = "S3_WORK_SUBMITTED"
    LOGGED_COMPLETED = "S10_LOGGED_COMPLETED"
    LOGGED_FAILED = "S11_LOGGED_FAILED"
    CANCELLED = "S12_CANCELLED"


def add_experience(user_id: int, amount: int, entry_type: str, quest_id: Optional[int] = None):
    """Insert an experience ledger entry."""
    cur = get_conn().cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO experience_ledger (user_id, amount, entry_type, quest_id, timestamp)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, entry_type, quest_id, now),
    )
    get_conn().commit()


def get_user_experience(user_id: int) -> int:
    """Return total experience for a user."""
    cur = get_conn().cursor()
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM experience_ledger WHERE user_id=?",
        (user_id,),
    )
    row = cur.fetchone()
    return row[0] if row else 0


def add_reputation(user_id: int, amount: int):
    """Adjust a user's reputation score."""
    cur = get_conn().cursor()
    cur.execute(
        "UPDATE users SET reputation = reputation + ? WHERE id=?",
        (amount, user_id),
    )
    get_conn().commit()


def get_user_by_id(user_id: int) -> models.User:
    """Fetch a single user by id."""
    cur = get_conn().cursor()
    cur.execute(
        "SELECT id, username, real_name, verified, role, reputation, created_at FROM users WHERE id=?",
        (user_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return models.User(
        id=row[0],
        username=row[1],
        real_name=row[2],
        verified=bool(row[3]),
        role=row[4],
        reputation=row[5],
        created_at=datetime.fromisoformat(row[6]),
    )


def run_decay(amount: int = WEEKLY_DECAY):
    """Apply weekly decay to all users."""
    cur = get_conn().cursor()
    cur.execute("SELECT id FROM users")
    users = [row[0] for row in cur.fetchall()]
    now = datetime.utcnow().isoformat()
    for uid in users:
        cur.execute(
            "INSERT INTO experience_ledger (user_id, amount, entry_type, quest_id, timestamp)"
            " VALUES (?, ?, 'decay', NULL, ?)",
            (uid, -amount, now),
        )
    get_conn().commit()


# Security dependency
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Get current user ID from JWT token."""
    user_id = auth.get_current_user_id(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user_id


@app.post("/auth/register", response_model=TokenResponse)
def register(user: UserRegister):
    """Register a new user with email and password."""
    cur = get_conn().cursor()
    
    # Check if username already exists
    cur.execute("SELECT id FROM users WHERE username=?", (user.username,))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email already exists
    cur.execute("SELECT id FROM users WHERE email=?", (user.email,))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Hash password
    password_hash = auth.hash_password(user.password)
    
    # Create user
    cur.execute(
        "INSERT INTO users (username, email, password_hash, real_name, verified, role, reputation, created_at)"
        " VALUES (?, ?, ?, ?, 0, ?, 0, ?)",
        (user.username, user.email, password_hash, user.real_name, user.role, datetime.utcnow().isoformat()),
    )
    get_conn().commit()
    user_id = cur.lastrowid
    
    # Grant initial experience points
    if user.role == "Organizer":
        add_experience(user_id, 20, "initial_grant", None)
    
    # Create and return token
    token = auth.create_token(user_id, user.username)
    return TokenResponse(token=token, user_id=user_id, username=user.username)


@app.post("/auth/login", response_model=TokenResponse)
def login(credentials: UserLogin):
    """Login with username and password."""
    cur = get_conn().cursor()
    
    # Get user by username
    cur.execute(
        "SELECT id, username, password_hash FROM users WHERE username=?",
        (credentials.username,)
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    user_id, username, password_hash = row
    
    # Verify password
    if not auth.verify_password(credentials.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Create and return token
    token = auth.create_token(user_id, username)
    return TokenResponse(token=token, user_id=user_id, username=username)


@app.post("/users", response_model=models.User)
def create_user(user: UserCreate):
    cur = get_conn().cursor()
    cur.execute(
        "INSERT INTO users (username, real_name, verified, role, reputation, created_at)"
        " VALUES (?, ?, 0, ?, 0, ?)",
        (user.username, user.real_name, user.role, datetime.utcnow().isoformat()),
    )
    get_conn().commit()
    user_id = cur.lastrowid
    return models.User(
        id=user_id,
        username=user.username,
        real_name=user.real_name,
        verified=False,
        role=user.role,
        reputation=0,
    )


@app.get("/users", response_model=List[models.User])
def list_users():
    cur = get_conn().cursor()
    cur.execute(
        "SELECT id, username, real_name, verified, role, reputation, created_at FROM users"
    )
    rows = cur.fetchall()
    return [
        models.User(
            id=row[0],
            username=row[1],
            real_name=row[2],
            verified=bool(row[3]),
            role=row[4],
            reputation=row[5],
            created_at=datetime.fromisoformat(row[6]),
        )
        for row in rows
    ]


@app.get("/users/{user_id}", response_model=models.User)
def get_user(user_id: int):
    return get_user_by_id(user_id)


@app.get("/me", response_model=models.User)
def get_current_user_info(current_user_id: int = Depends(get_current_user)):
    """Get current authenticated user's information."""
    return get_user_by_id(current_user_id)


@app.post("/quests", response_model=models.Quest)
def create_quest(quest: QuestCreate, current_user_id: int = Depends(get_current_user)):
    # Check if user has enough experience to create a quest
    user_xp = get_user_experience(current_user_id)
    if user_xp < QUEST_CREATION_COST:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient experience. Need {QUEST_CREATION_COST} XP, have {user_xp} XP"
        )

    now = datetime.utcnow().isoformat()
    cur = get_conn().cursor()
    cur.execute(
        "INSERT INTO quests (title, description, reward, creator_id, status, category, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            quest.title,
            quest.description,
            quest.reward,
            current_user_id,
            QuestStatus.OPEN.value,
            quest.category or "general",  # Default category
            now,
            now,
        ),
    )
    get_conn().commit()
    quest_id = cur.lastrowid
    
    # Deduct experience points for quest creation
    add_experience(current_user_id, -QUEST_CREATION_COST, "quest_creation", quest_id)
    
    return get_quest_by_id(quest_id)


@app.post("/quests/{quest_id}/claim", response_model=models.Quest)
def claim_quest(quest_id: int, current_user_id: int = Depends(get_current_user)):
    cur = get_conn().cursor()
    cur.execute("SELECT status FROM quests WHERE id=?", (quest_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="quest not found")
    status = row[0]
    if status != QuestStatus.OPEN.value:
        raise HTTPException(status_code=400, detail="quest not open")

    now = datetime.utcnow().isoformat()
    cur.execute(
        "UPDATE quests SET performer_id=?, status=?, updated_at=? WHERE id=?",
        (current_user_id, QuestStatus.CLAIMED.value, now, quest_id),
    )
    get_conn().commit()
    return get_quest_by_id(quest_id)


def get_quest_by_id(quest_id: int) -> models.Quest:
    cur = get_conn().cursor()
    cur.execute(
        "SELECT id, title, description, reward, creator_id, performer_id, verifier_id, status, created_at, updated_at, category, visibility, boost_level FROM quests WHERE id=?",
        (quest_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="quest not found")
    return models.Quest(
        id=row[0],
        title=row[1],
        description=row[2],
        reward=row[3],
        creator_id=row[4],
        performer_id=row[5],
        verifier_id=row[6],
        status=row[7],
        created_at=datetime.fromisoformat(row[8]),
        updated_at=datetime.fromisoformat(row[9]),
        category=row[10],
        visibility=row[11],
        boost_level=row[12],
    )


@app.post("/quests/{quest_id}/submit", response_model=models.Quest)
def submit_work(quest_id: int, current_user_id: int = Depends(get_current_user)):
    cur = get_conn().cursor()
    cur.execute(
        "SELECT performer_id, status FROM quests WHERE id=?",
        (quest_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="quest not found")
    performer_id, status = row
    if performer_id != current_user_id:
        raise HTTPException(status_code=400, detail="not quest performer")
    if status != QuestStatus.CLAIMED.value:
        raise HTTPException(status_code=400, detail="invalid state")
    now = datetime.utcnow().isoformat()
    cur.execute(
        "UPDATE quests SET status=?, updated_at=? WHERE id=?",
        (QuestStatus.WORK_SUBMITTED.value, now, quest_id),
    )
    get_conn().commit()
    return get_quest_by_id(quest_id)


@app.post("/quests/{quest_id}/verify", response_model=models.Quest)
def verify_quest(quest_id: int, req: VerificationRequest, current_user_id: int = Depends(get_current_user)):
    cur = get_conn().cursor()
    cur.execute(
        "SELECT performer_id, status FROM quests WHERE id=?",
        (quest_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="quest not found")
    performer_id, status = row
    if status != QuestStatus.WORK_SUBMITTED.value:
        raise HTTPException(status_code=400, detail="quest not ready for verification")
    if req.result not in {"normal", "exceptional", "failed"}:
        raise HTTPException(status_code=400, detail="invalid result")

    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO verifications (quest_id, verifier_id, performer_id, result, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (quest_id, current_user_id, performer_id, req.result, now),
    )
    if req.result == "failed":
        final_status = QuestStatus.LOGGED_FAILED.value
        add_reputation(performer_id, -1)
    else:
        final_status = QuestStatus.LOGGED_COMPLETED.value
        reward = 10 if req.result == "normal" else 20
        add_experience(performer_id, reward, "quest_reward", quest_id)
        add_experience(current_user_id, reward // 2, "verification_reward", quest_id)
        rep_gain = 1 if req.result == "normal" else 2
        add_reputation(performer_id, rep_gain)
        add_reputation(current_user_id, rep_gain // 2 or 1)
    cur.execute(
        "UPDATE quests SET verifier_id=?, status=?, updated_at=? WHERE id=?",
        (current_user_id, final_status, now, quest_id),
    )
    get_conn().commit()
    return get_quest_by_id(quest_id)


@app.get("/quests", response_model=List[models.Quest])
def list_quests(category: Optional[str] = None):
    cur = get_conn().cursor()
    
    if category:
        cur.execute(
            "SELECT id, title, description, reward, creator_id, performer_id, verifier_id, status, created_at, updated_at, category, visibility, boost_level FROM quests WHERE category=? ORDER BY boost_level DESC, created_at DESC",
            (category,)
        )
    else:
        cur.execute(
            "SELECT id, title, description, reward, creator_id, performer_id, verifier_id, status, created_at, updated_at, category, visibility, boost_level FROM quests ORDER BY boost_level DESC, created_at DESC"
        )
    
    rows = cur.fetchall()
    return [
        models.Quest(
            id=row[0],
            title=row[1],
            description=row[2],
            reward=row[3],
            creator_id=row[4],
            performer_id=row[5],
            verifier_id=row[6],
            status=row[7],
            created_at=datetime.fromisoformat(row[8]),
            updated_at=datetime.fromisoformat(row[9]),
            category=row[10],
            visibility=row[11],
            boost_level=row[12],
        )
        for row in rows
    ]


@app.get("/quests/{quest_id}", response_model=models.Quest)
def get_quest(quest_id: int):
    return get_quest_by_id(quest_id)


@app.get("/users/{user_id}/experience")
def get_user_experience_balance(user_id: int):
    """Get a user's current experience balance."""
    # Ensure user exists
    cur = get_conn().cursor()
    cur.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="user not found")
    
    balance = get_user_experience(user_id)
    return {"user_id": user_id, "experience_balance": balance}


@app.post("/quests/{quest_id}/boost")
def boost_quest(quest_id: int, current_user_id: int = Depends(get_current_user)):
    """Boost a quest to increase its visibility (costs experience points)."""
    # Ensure quest exists
    quest = get_quest_by_id(quest_id)
    
    # Check if user has enough experience
    user_xp = get_user_experience(current_user_id)
    if user_xp < QUEST_BOOST_COST:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient experience. Need {QUEST_BOOST_COST} XP, have {user_xp} XP"
        )
    
    # Deduct the XP and update boost level
    add_experience(current_user_id, -QUEST_BOOST_COST, "quest_boost", quest_id)
    
    # Update quest boost_level
    cur = get_conn().cursor()
    cur.execute(
        "UPDATE quests SET boost_level = boost_level + 1 WHERE id=?",
        (quest_id,)
    )
    get_conn().commit()
    
    return {"message": "Quest boosted successfully", "cost": QUEST_BOOST_COST}


@app.get("/categories")
def list_categories():
    """Get list of available quest categories with counts."""
    cur = get_conn().cursor()
    cur.execute("""
        SELECT category, COUNT(*) as count 
        FROM quests 
        WHERE category IS NOT NULL 
        GROUP BY category 
        ORDER BY count DESC
    """)
    
    categories = [
        {"name": row[0], "count": row[1]}
        for row in cur.fetchall()
    ]
    
    # Add predefined categories even if they have no quests yet
    predefined = ["civic", "environmental", "social", "educational", "technical", "general"]
    existing = {cat["name"] for cat in categories}
    
    for cat_name in predefined:
        if cat_name not in existing:
            categories.append({"name": cat_name, "count": 0})
    
    return {"categories": categories}


@app.get("/stats/board")
def get_board_stats():
    """Get board-wide statistics."""
    cur = get_conn().cursor()
    
    # Total quests by status
    cur.execute("""
        SELECT status, COUNT(*) as count 
        FROM quests 
        GROUP BY status
    """)
    quests_by_status = {row[0]: row[1] for row in cur.fetchall()}
    
    # Total users by role
    cur.execute("""
        SELECT role, COUNT(*) as count 
        FROM users 
        GROUP BY role
    """)
    users_by_role = {row[0]: row[1] for row in cur.fetchall()}
    
    # Total XP in circulation
    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM experience_ledger")
    total_xp = cur.fetchone()[0]
    
    # Active users (those who have earned or spent XP)
    cur.execute("""
        SELECT COUNT(DISTINCT user_id) 
        FROM experience_ledger 
        WHERE timestamp > datetime('now', '-7 days')
    """)
    active_users_week = cur.fetchone()[0]
    
    # Quest completion rate
    total_quests = sum(quests_by_status.values())
    completed_quests = quests_by_status.get("S10_LOGGED_COMPLETED", 0)
    completion_rate = (completed_quests / total_quests * 100) if total_quests > 0 else 0
    
    # Category distribution
    cur.execute("""
        SELECT category, COUNT(*) as count 
        FROM quests 
        WHERE category IS NOT NULL 
        GROUP BY category
    """)
    quests_by_category = {row[0]: row[1] for row in cur.fetchall()}
    
    return {
        "quests": {
            "total": total_quests,
            "by_status": quests_by_status,
            "by_category": quests_by_category,
            "completion_rate": round(completion_rate, 2)
        },
        "users": {
            "total": sum(users_by_role.values()),
            "by_role": users_by_role,
            "active_this_week": active_users_week
        },
        "experience": {
            "total_in_circulation": total_xp
        }
    }


@app.get("/stats/user/{user_id}")
def get_user_stats(user_id: int):
    """Get statistics for a specific user."""
    # Ensure user exists
    user = get_user_by_id(user_id)
    
    cur = get_conn().cursor()
    
    # Quests created
    cur.execute("SELECT COUNT(*) FROM quests WHERE creator_id=?", (user_id,))
    quests_created = cur.fetchone()[0]
    
    # Quests performed
    cur.execute("SELECT COUNT(*) FROM quests WHERE performer_id=? AND status='S10_LOGGED_COMPLETED'", (user_id,))
    quests_completed = cur.fetchone()[0]
    
    # Quests verified
    cur.execute("SELECT COUNT(*) FROM quests WHERE verifier_id=?", (user_id,))
    quests_verified = cur.fetchone()[0]
    
    # Experience history
    cur.execute("""
        SELECT entry_type, SUM(amount) as total 
        FROM experience_ledger 
        WHERE user_id=? 
        GROUP BY entry_type
    """, (user_id,))
    xp_by_type = {row[0]: row[1] for row in cur.fetchall()}
    
    # Current balance
    current_xp = get_user_experience(user_id)
    
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "reputation": user.reputation
        },
        "quests": {
            "created": quests_created,
            "completed": quests_completed,
            "verified": quests_verified
        },
        "experience": {
            "current_balance": current_xp,
            "by_type": xp_by_type
        }
    }
