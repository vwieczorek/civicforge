from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict


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


class InviteCreate(BaseModel):
    board_id: str = "board_001"  # Default to primary board for MVP
    role: str = "friend"
    email: Optional[str] = None
    max_uses: int = 1
    expires_hours: int = 48


class InviteResponse(BaseModel):
    invite_url: str
    expires_at: datetime
    role: str


class JoinBoardRequest(BaseModel):
    token: str


class BoardMemberResponse(BaseModel):
    id: int
    user_id: int
    username: str
    real_name: str
    role: str
    permissions: Dict[str, bool]
    joined_at: datetime


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


def get_board_membership(board_id: str, user_id: int) -> Optional[Dict]:
    """Get a user's membership for a board."""
    db = get_db()
    row = db.fetchone(
        "SELECT id, role, permissions FROM board_memberships WHERE board_id=? AND user_id=?",
        (board_id, user_id)
    )
    if row:
        import json
        permissions = json.loads(row['permissions']) if isinstance(row['permissions'], str) else row['permissions']
        return {
            'id': row['id'],
            'role': row['role'],
            'permissions': permissions
        }
    return None


def check_board_permission(board_id: str, user_id: int, permission: str) -> bool:
    """Check if a user has a specific permission on a board."""
    membership = get_board_membership(board_id, user_id)
    if not membership:
        # Check if user is board owner (first user to create content on board)
        db = get_db()
        first_quest = db.fetchone(
            "SELECT creator_id FROM quests ORDER BY created_at LIMIT 1"
        )
        if first_quest and first_quest['creator_id'] == user_id:
            # Grant owner permissions to first quest creator
            return auth.check_permission(auth.ROLE_PERMISSIONS['owner'], permission)
        
        # Default permissions for all authenticated users (participant level)
        return auth.check_permission(auth.ROLE_PERMISSIONS['participant'], permission)
    return auth.check_permission(membership['permissions'], permission)


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


@app.post("/boards/{board_id}/invites", response_model=InviteResponse)
def create_board_invite(
    board_id: str,
    invite_data: InviteCreate,
    current_user_id: int = Depends(get_current_user)
):
    """Create an invitation to join a board."""
    # Check if user has permission to create invites
    if not check_board_permission(board_id, current_user_id, "create_invites"):
        raise HTTPException(status_code=403, detail="No permission to create invites")
    
    # Create invite
    invite = auth.create_board_invite(
        board_id=board_id,
        created_by_user_id=current_user_id,
        role=invite_data.role,
        email=invite_data.email,
        max_uses=invite_data.max_uses,
        expires_hours=invite_data.expires_hours
    )
    
    # Save to database
    db = get_db()
    import json
    db.execute(
        """INSERT INTO board_invites 
        (board_id, created_by_user_id, invite_token, email, role, permissions, max_uses, used_count, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            invite['board_id'],
            invite['created_by_user_id'],
            invite['invite_token'],
            invite['email'],
            invite['role'],
            json.dumps(invite['permissions']),
            invite['max_uses'],
            invite['used_count'],
            invite['expires_at'].isoformat(),
            invite['created_at'].isoformat()
        )
    )
    db.commit()
    
    # Generate invite URL
    base_url = os.environ.get("BASE_URL", "http://localhost:8000")
    invite_url = f"{base_url}/board/{board_id}/join?token={invite['invite_token']}"
    
    return InviteResponse(
        invite_url=invite_url,
        expires_at=invite['expires_at'],
        role=invite['role']
    )


@app.post("/boards/{board_id}/join")
def join_board(
    board_id: str,
    join_request: JoinBoardRequest,
    current_user_id: int = Depends(get_current_user)
):
    """Accept an invitation to join a board."""
    db = get_db()
    
    # Get invite by token
    row = db.fetchone(
        "SELECT * FROM board_invites WHERE board_id=? AND invite_token=?",
        (board_id, join_request.token)
    )
    
    if not row:
        raise HTTPException(status_code=404, detail="Invalid invite")
    
    # Convert row to dict for validation
    import json
    invite = {
        'id': row['id'],
        'board_id': row['board_id'],
        'created_by_user_id': row['created_by_user_id'],
        'invite_token': row['invite_token'],
        'email': row['email'],
        'role': row['role'],
        'permissions': json.loads(row['permissions']) if isinstance(row['permissions'], str) else row['permissions'],
        'max_uses': row['max_uses'],
        'used_count': row['used_count'],
        'expires_at': row['expires_at'],
        'created_at': row['created_at']
    }
    
    # Validate invite
    if not auth.validate_invite_token(invite):
        raise HTTPException(status_code=400, detail="Invite expired or already used")
    
    # Check if already member
    existing = get_board_membership(board_id, current_user_id)
    if existing:
        raise HTTPException(status_code=400, detail="Already a board member")
    
    # Create membership
    with db.transaction():
        db.execute(
            """INSERT INTO board_memberships 
            (board_id, user_id, role, permissions, invited_by_user_id, invite_id, joined_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                board_id,
                current_user_id,
                invite['role'],
                json.dumps(invite['permissions']),
                invite['created_by_user_id'],
                invite['id'],
                datetime.utcnow().isoformat()
            )
        )
        
        # Increment invite usage
        db.execute(
            "UPDATE board_invites SET used_count = used_count + 1 WHERE id=?",
            (invite['id'],)
        )
    
    return {"message": "Successfully joined board", "role": invite['role']}


@app.get("/boards/{board_id}/members", response_model=List[BoardMemberResponse])
def list_board_members(
    board_id: str,
    current_user_id: int = Depends(get_current_user)
):
    """List all members of a board."""
    # Check if user has permission to view members
    if not check_board_permission(board_id, current_user_id, "view_board"):
        raise HTTPException(status_code=403, detail="No permission to view board members")
    
    db = get_db()
    rows = db.fetchall(
        """SELECT m.id, m.user_id, m.role, m.permissions, m.joined_at,
                  u.username, u.real_name
           FROM board_memberships m
           JOIN users u ON m.user_id = u.id
           WHERE m.board_id = ?
           ORDER BY m.joined_at DESC""",
        (board_id,)
    )
    
    import json
    members = []
    for row in rows:
        permissions = json.loads(row['permissions']) if isinstance(row['permissions'], str) else row['permissions']
        members.append(BoardMemberResponse(
            id=row['id'],
            user_id=row['user_id'],
            username=row['username'],
            real_name=row['real_name'],
            role=row['role'],
            permissions=permissions,
            joined_at=safe_datetime(row['joined_at'])
        ))
    
    return members


@app.delete("/boards/{board_id}/members/{user_id}")
def remove_board_member(
    board_id: str,
    user_id: int,
    current_user_id: int = Depends(get_current_user)
):
    """Remove a member from a board."""
    # Check if user has permission to manage members
    if not check_board_permission(board_id, current_user_id, "manage_members"):
        raise HTTPException(status_code=403, detail="No permission to manage members")
    
    # Prevent removing self if you're the only owner
    if user_id == current_user_id:
        db = get_db()
        owner_count = db.fetchone(
            "SELECT COUNT(*) as count FROM board_memberships WHERE board_id=? AND role='owner'",
            (board_id,)
        )
        if owner_count['count'] <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the only board owner")
    
    db = get_db()
    # First check if member exists
    existing = db.fetchone(
        "SELECT user_id FROM board_memberships WHERE board_id=? AND user_id=?",
        (board_id, user_id)
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Delete the member
    db.execute(
        "DELETE FROM board_memberships WHERE board_id=? AND user_id=?",
        (board_id, user_id)
    )
    db.commit()
    
    return {"message": "Member removed successfully"}


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


class UserWithMembership(BaseModel):
    """Extended user info including board membership."""
    id: int
    username: str
    real_name: str
    verified: bool
    role: str
    reputation: int
    created_at: datetime
    board_membership: Optional[Dict] = None
    experience_balance: int = 0


@app.get("/me", response_model=UserWithMembership)
def get_current_user_info(current_user_id: int = Depends(get_current_user)):
    """Get current authenticated user's information including board membership."""
    user = get_user_by_id(current_user_id)
    
    # Get board membership for default board
    board_id = "board_001"
    membership = get_board_membership(board_id, current_user_id)
    
    # Get experience balance
    experience_balance = get_user_experience(current_user_id)
    
    return UserWithMembership(
        id=user.id,
        username=user.username,
        real_name=user.real_name,
        verified=user.verified,
        role=user.role,
        reputation=user.reputation,
        created_at=user.created_at,
        board_membership=membership,
        experience_balance=experience_balance
    )


@app.post("/quests", response_model=models.Quest)
def create_quest(quest: QuestCreate, current_user_id: int = Depends(get_current_user)):
    # Check if user has permission to create quests on the board
    board_id = "board_001"  # Default board for MVP
    if not check_board_permission(board_id, current_user_id, "create_quest"):
        raise HTTPException(status_code=403, detail="No permission to create quests")
    
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
    # Check if user has permission to claim quests
    board_id = "board_001"  # Default board for MVP
    if not check_board_permission(board_id, current_user_id, "claim_quest"):
        raise HTTPException(status_code=403, detail="No permission to claim quests")
    
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
    # Check if user has permission to verify quests
    board_id = "board_001"  # Default board for MVP
    if not check_board_permission(board_id, current_user_id, "verify_quest"):
        raise HTTPException(status_code=403, detail="No permission to verify quests")
    
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