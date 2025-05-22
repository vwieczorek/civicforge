from enum import Enum
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import os
from . import models

app = FastAPI(title="CivicForge Board MVP")

# Initialize database when the module is imported. The path can be overridden
# with the ``BOARD_DB_PATH`` environment variable for testing purposes.
DB_PATH = os.environ.get("BOARD_DB_PATH", models.DB_PATH)
conn = models.init_db(DB_PATH)

# Weekly decay amount for experience points
WEEKLY_DECAY = 1


class UserCreate(BaseModel):
    username: str
    real_name: str
    role: str


class QuestCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    reward: int = 0
    creator_id: int


class ClaimRequest(BaseModel):
    performer_id: int


class SubmitRequest(BaseModel):
    performer_id: int


class VerificationRequest(BaseModel):
    verifier_id: int
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
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO experience_ledger (user_id, amount, entry_type, quest_id, timestamp)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, entry_type, quest_id, now),
    )
    conn.commit()


def get_user_experience(user_id: int) -> int:
    """Return total experience for a user."""
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM experience_ledger WHERE user_id=?",
        (user_id,),
    )
    row = cur.fetchone()
    return row[0] if row else 0


def run_decay(amount: int = WEEKLY_DECAY):
    """Apply weekly decay to all users."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM users")
    users = [row[0] for row in cur.fetchall()]
    now = datetime.utcnow().isoformat()
    for uid in users:
        cur.execute(
            "INSERT INTO experience_ledger (user_id, amount, entry_type, quest_id, timestamp)"
            " VALUES (?, ?, 'decay', NULL, ?)",
            (uid, -amount, now),
        )
    conn.commit()


@app.post("/users", response_model=models.User)
def create_user(user: UserCreate):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, real_name, verified, role, reputation, created_at)"
        " VALUES (?, ?, 0, ?, 0, ?)",
        (user.username, user.real_name, user.role, datetime.utcnow().isoformat()),
    )
    conn.commit()
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
    cur = conn.cursor()
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


@app.post("/quests", response_model=models.Quest)
def create_quest(quest: QuestCreate):
    # Ensure creator exists
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE id=?", (quest.creator_id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="creator not found")

    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO quests (title, description, reward, creator_id, status, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            quest.title,
            quest.description,
            quest.reward,
            quest.creator_id,
            QuestStatus.OPEN.value,
            now,
            now,
        ),
    )
    conn.commit()
    quest_id = cur.lastrowid
    return get_quest_by_id(quest_id)


@app.post("/quests/{quest_id}/claim", response_model=models.Quest)
def claim_quest(quest_id: int, claim: ClaimRequest):
    cur = conn.cursor()
    cur.execute("SELECT status FROM quests WHERE id=?", (quest_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="quest not found")
    status = row[0]
    if status != QuestStatus.OPEN.value:
        raise HTTPException(status_code=400, detail="quest not open")
    # ensure performer exists
    cur.execute("SELECT id FROM users WHERE id=?", (claim.performer_id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="performer not found")

    now = datetime.utcnow().isoformat()
    cur.execute(
        "UPDATE quests SET performer_id=?, status=?, updated_at=? WHERE id=?",
        (claim.performer_id, QuestStatus.CLAIMED.value, now, quest_id),
    )
    conn.commit()
    return get_quest_by_id(quest_id)


def get_quest_by_id(quest_id: int) -> models.Quest:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, description, reward, creator_id, performer_id, verifier_id, status, created_at, updated_at FROM quests WHERE id=?",
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
    )


@app.post("/quests/{quest_id}/submit", response_model=models.Quest)
def submit_work(quest_id: int, req: SubmitRequest):
    cur = conn.cursor()
    cur.execute(
        "SELECT performer_id, status FROM quests WHERE id=?",
        (quest_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="quest not found")
    performer_id, status = row
    if performer_id != req.performer_id:
        raise HTTPException(status_code=400, detail="not quest performer")
    if status != QuestStatus.CLAIMED.value:
        raise HTTPException(status_code=400, detail="invalid state")
    now = datetime.utcnow().isoformat()
    cur.execute(
        "UPDATE quests SET status=?, updated_at=? WHERE id=?",
        (QuestStatus.WORK_SUBMITTED.value, now, quest_id),
    )
    conn.commit()
    return get_quest_by_id(quest_id)


@app.post("/quests/{quest_id}/verify", response_model=models.Quest)
def verify_quest(quest_id: int, req: VerificationRequest):
    cur = conn.cursor()
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
    # ensure verifier exists
    cur.execute("SELECT id FROM users WHERE id=?", (req.verifier_id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="verifier not found")

    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO verifications (quest_id, verifier_id, performer_id, result, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (quest_id, req.verifier_id, performer_id, req.result, now),
    )
    if req.result == "failed":
        final_status = QuestStatus.LOGGED_FAILED.value
    else:
        final_status = QuestStatus.LOGGED_COMPLETED.value
        reward = 10 if req.result == "normal" else 20
        add_experience(performer_id, reward, "quest_reward", quest_id)
        add_experience(req.verifier_id, reward // 2, "verification_reward", quest_id)
    cur.execute(
        "UPDATE quests SET verifier_id=?, status=?, updated_at=? WHERE id=?",
        (req.verifier_id, final_status, now, quest_id),
    )
    conn.commit()
    return get_quest_by_id(quest_id)


@app.get("/quests", response_model=List[models.Quest])
def list_quests():
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, description, reward, creator_id, performer_id, verifier_id, status, created_at, updated_at FROM quests"
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
        )
        for row in rows
    ]


@app.get("/quests/{quest_id}", response_model=models.Quest)
def get_quest(quest_id: int):
    return get_quest_by_id(quest_id)
