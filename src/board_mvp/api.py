from enum import Enum
from datetime import datetime
from typing import Optional, List


def safe_datetime(value):
    """Safely convert a value to datetime, handling both datetime objects and strings."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

import os
from fastapi.middleware.cors import CORSMiddleware
from . import models
from . import auth
from .database import get_db, Database, init_db

app = FastAPI(title="CivicForge Board MVP")

# CORS configuration (for separate frontend applications)
cors_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
if cors_origins:
    origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Initialize the database
init_db()

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
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO experience_ledger (user_id, amount, entry_type, quest_id, timestamp)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, entry_type, quest_id, now),
    )
    db.commit()


def get_user_experience(user_id: int) -> int:
    """Return total experience for a user."""
    db = get_db()
    result = db.fetchone(
        "SELECT COALESCE(SUM(amount), 0) as total FROM experience_ledger WHERE user_id=?",
        (user_id,),
    )
    return result['total'] if result else 0


def add_reputation(user_id: int, amount: int):
    """Adjust a user's reputation score."""
    db = get_db()
    db.execute(
        "UPDATE users SET reputation = reputation + ? WHERE id=?",
        (amount, user_id),
    )
    db.commit()


def get_user_by_id(user_id: int) -> models.User:
    """Fetch a single user by id."""
    db = get_db()
    row = db.fetchone(
        "SELECT id, username, real_name, verified, role, reputation, created_at FROM users WHERE id=?",
        (user_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return models.User(
        id=row['id'],
        username=row['username'],
        real_name=row['real_name'],
        verified=bool(row['verified']),
        role=row['role'],
        reputation=row['reputation'],
        created_at=safe_datetime(row['created_at']),
    )


def run_decay(amount: int = WEEKLY_DECAY):
    """Apply weekly decay to all users."""
    db = get_db()
    users = db.fetchall("SELECT id FROM users")
    now = datetime.utcnow().isoformat()
    
    # Prepare batch insert data
    decay_entries = [
        (uid['id'], -amount, 'decay', None, now)
        for uid in users
    ]
    
    if decay_entries:
        db.executemany(
            "INSERT INTO experience_ledger (user_id, amount, entry_type, quest_id, timestamp)"
            " VALUES (?, ?, ?, ?, ?)",
            decay_entries
        )
        db.commit()


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
    db = get_db()
    
    # Check if username already exists
    existing = db.fetchone("SELECT id FROM users WHERE username=?", (user.username,))
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email already exists
    existing = db.fetchone("SELECT id FROM users WHERE email=?", (user.email,))
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Hash password
    password_hash = auth.hash_password(user.password)
    
    # Create user
    db.execute(
        "INSERT INTO users (username, email, password_hash, real_name, verified, role, reputation, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user.username, user.email, password_hash, user.real_name, False, user.role, 0, datetime.utcnow().isoformat()),
    )
    db.commit()
    user_id = db.adapter.lastrowid
    
    # Grant initial experience points
    if user.role == "Organizer":
        add_experience(user_id, 20, "initial_grant", None)
    
    # Create and return token
    token = auth.create_token(user_id, user.username)
    return TokenResponse(token=token, user_id=user_id, username=user.username)


@app.post("/auth/login", response_model=TokenResponse)
def login(credentials: UserLogin):
    """Login with username and password."""
    db = get_db()
    
    # Get user by username
    row = db.fetchone(
        "SELECT id, username, password_hash FROM users WHERE username=?",
        (credentials.username,)
    )
    if not row:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    user_id = row['id']
    username = row['username']
    password_hash = row['password_hash']
    
    # Verify password
    if not auth.verify_password(credentials.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Create and return token
    token = auth.create_token(user_id, username)
    return TokenResponse(token=token, user_id=user_id, username=username)


@app.post("/users", response_model=models.User)
def create_user(user: UserCreate):
    db = get_db()
    db.execute(
        "INSERT INTO users (username, real_name, verified, role, reputation, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (user.username, user.real_name, False, user.role, 0, datetime.utcnow().isoformat()),
    )
    db.commit()
    user_id = db.adapter.lastrowid
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
    db = get_db()
    rows = db.fetchall(
        "SELECT id, username, real_name, verified, role, reputation, created_at FROM users"
    )
    return [
        models.User(
            id=row['id'],
            username=row['username'],
            real_name=row['real_name'],
            verified=bool(row['verified']),
            role=row['role'],
            reputation=row['reputation'],
            created_at=safe_datetime(row['created_at']),
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
    db = get_db()
    db.execute(
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
    db.commit()
    quest_id = db.adapter.lastrowid
    
    # Deduct experience points for quest creation
    add_experience(current_user_id, -QUEST_CREATION_COST, "quest_creation", quest_id)
    
    return get_quest_by_id(quest_id)


@app.post("/quests/{quest_id}/claim", response_model=models.Quest)
def claim_quest(quest_id: int, current_user_id: int = Depends(get_current_user)):
    db = get_db()
    row = db.fetchone("SELECT status FROM quests WHERE id=?", (quest_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="quest not found")
    status = row['status']
    if status != QuestStatus.OPEN.value:
        raise HTTPException(status_code=400, detail="quest not open")

    now = datetime.utcnow().isoformat()
    db.execute(
        "UPDATE quests SET performer_id=?, status=?, updated_at=? WHERE id=?",
        (current_user_id, QuestStatus.CLAIMED.value, now, quest_id),
    )
    db.commit()
    return get_quest_by_id(quest_id)


def get_quest_by_id(quest_id: int) -> models.Quest:
    db = get_db()
    row = db.fetchone(
        "SELECT id, title, description, reward, creator_id, performer_id, verifier_id, status, created_at, updated_at, category, visibility, boost_level FROM quests WHERE id=?",
        (quest_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="quest not found")
    return models.Quest(
        id=row['id'],
        title=row['title'],
        description=row['description'],
        reward=row['reward'],
        creator_id=row['creator_id'],
        performer_id=row['performer_id'],
        verifier_id=row['verifier_id'],
        status=row['status'],
        created_at=safe_datetime(row['created_at']),
        updated_at=safe_datetime(row['updated_at']),
        category=row['category'],
        visibility=row['visibility'],
        boost_level=row['boost_level'],
    )


@app.post("/quests/{quest_id}/submit", response_model=models.Quest)
def submit_work(quest_id: int, current_user_id: int = Depends(get_current_user)):
    db = get_db()
    row = db.fetchone(
        "SELECT performer_id, status FROM quests WHERE id=?",
        (quest_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="quest not found")
    performer_id = row['performer_id']
    status = row['status']
    if performer_id != current_user_id:
        raise HTTPException(status_code=400, detail="not quest performer")
    if status != QuestStatus.CLAIMED.value:
        raise HTTPException(status_code=400, detail="invalid state")
    now = datetime.utcnow().isoformat()
    db.execute(
        "UPDATE quests SET status=?, updated_at=? WHERE id=?",
        (QuestStatus.WORK_SUBMITTED.value, now, quest_id),
    )
    db.commit()
    return get_quest_by_id(quest_id)


@app.post("/quests/{quest_id}/verify", response_model=models.Quest)
def verify_quest(quest_id: int, req: VerificationRequest, current_user_id: int = Depends(get_current_user)):
    db = get_db()
    row = db.fetchone(
        "SELECT performer_id, status FROM quests WHERE id=?",
        (quest_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="quest not found")
    performer_id = row['performer_id']
    status = row['status']
    if status != QuestStatus.WORK_SUBMITTED.value:
        raise HTTPException(status_code=400, detail="quest not ready for verification")
    if req.result not in {"normal", "exceptional", "failed"}:
        raise HTTPException(status_code=400, detail="invalid result")

    now = datetime.utcnow().isoformat()
    
    # Use transaction for verification process
    with db.transaction():
        db.execute(
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
        
        db.execute(
            "UPDATE quests SET verifier_id=?, status=?, updated_at=? WHERE id=?",
            (current_user_id, final_status, now, quest_id),
        )
    
    return get_quest_by_id(quest_id)


@app.get("/quests", response_model=List[models.Quest])
def list_quests(category: Optional[str] = None):
    db = get_db()
    
    if category:
        rows = db.fetchall(
            "SELECT id, title, description, reward, creator_id, performer_id, verifier_id, status, created_at, updated_at, category, visibility, boost_level FROM quests WHERE category=? ORDER BY boost_level DESC, created_at DESC",
            (category,)
        )
    else:
        rows = db.fetchall(
            "SELECT id, title, description, reward, creator_id, performer_id, verifier_id, status, created_at, updated_at, category, visibility, boost_level FROM quests ORDER BY boost_level DESC, created_at DESC"
        )
    
    return [
        models.Quest(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            reward=row['reward'],
            creator_id=row['creator_id'],
            performer_id=row['performer_id'],
            verifier_id=row['verifier_id'],
            status=row['status'],
            created_at=safe_datetime(row['created_at']),
            updated_at=safe_datetime(row['updated_at']),
            category=row['category'],
            visibility=row['visibility'],
            boost_level=row['boost_level'],
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
    db = get_db()
    if not db.fetchone("SELECT id FROM users WHERE id=?", (user_id,)):
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
    db = get_db()
    db.execute(
        "UPDATE quests SET boost_level = boost_level + 1 WHERE id=?",
        (quest_id,)
    )
    db.commit()
    
    return {"message": "Quest boosted successfully", "cost": QUEST_BOOST_COST}


@app.get("/categories")
def list_categories():
    """Get list of available quest categories with counts."""
    db = get_db()
    rows = db.fetchall("""
        SELECT category, COUNT(*) as count 
        FROM quests 
        WHERE category IS NOT NULL 
        GROUP BY category 
        ORDER BY count DESC
    """)
    
    categories = [
        {"name": row['category'], "count": row['count']}
        for row in rows
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
    db = get_db()
    
    # Total quests by status
    status_rows = db.fetchall("""
        SELECT status, COUNT(*) as count 
        FROM quests 
        GROUP BY status
    """)
    quests_by_status = {row['status']: row['count'] for row in status_rows}
    
    # Total users by role
    role_rows = db.fetchall("""
        SELECT role, COUNT(*) as count 
        FROM users 
        GROUP BY role
    """)
    users_by_role = {row['role']: row['count'] for row in role_rows}
    
    # Total XP in circulation
    xp_result = db.fetchone("SELECT COALESCE(SUM(amount), 0) as total FROM experience_ledger")
    total_xp = xp_result['total'] if xp_result else 0
    
    # Active users (those who have earned or spent XP)
    active_result = db.fetchone("""
        SELECT COUNT(DISTINCT user_id) as count 
        FROM experience_ledger 
        WHERE timestamp > NOW() - INTERVAL '7 days'
    """)
    active_users_week = active_result['count'] if active_result else 0
    
    # Quest completion rate
    total_quests = sum(quests_by_status.values())
    completed_quests = quests_by_status.get("S10_LOGGED_COMPLETED", 0)
    completion_rate = (completed_quests / total_quests * 100) if total_quests > 0 else 0
    
    # Category distribution
    cat_rows = db.fetchall("""
        SELECT category, COUNT(*) as count 
        FROM quests 
        WHERE category IS NOT NULL 
        GROUP BY category
    """)
    quests_by_category = {row['category']: row['count'] for row in cat_rows}
    
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
    
    db = get_db()
    
    # Quests created
    created_result = db.fetchone("SELECT COUNT(*) as count FROM quests WHERE creator_id=?", (user_id,))
    quests_created = created_result['count'] if created_result else 0
    
    # Quests performed
    completed_result = db.fetchone("SELECT COUNT(*) as count FROM quests WHERE performer_id=? AND status='S10_LOGGED_COMPLETED'", (user_id,))
    quests_completed = completed_result['count'] if completed_result else 0
    
    # Quests verified
    verified_result = db.fetchone("SELECT COUNT(*) as count FROM quests WHERE verifier_id=?", (user_id,))
    quests_verified = verified_result['count'] if verified_result else 0
    
    # Experience history
    xp_rows = db.fetchall("""
        SELECT entry_type, SUM(amount) as total 
        FROM experience_ledger 
        WHERE user_id=? 
        GROUP BY entry_type
    """, (user_id,))
    xp_by_type = {row['entry_type']: row['total'] for row in xp_rows}
    
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


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Test database connection
        db = get_db()
        result = db.fetchone("SELECT 1 as health_check")
        if result and result['health_check'] == 1:
            return {"status": "healthy", "database": "connected"}
        else:
            raise HTTPException(status_code=503, detail="Database check failed")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")