import os
from board_mvp import api

"""Seed the board database with initial users and quests for project tracking."""


def ensure_user(username: str, real_name: str, role: str) -> api.models.User:
    """Create a user if it doesn't already exist."""
    cur = api.conn.cursor()
    cur.execute("SELECT id FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    if row:
        return api.get_user_by_id(row[0])
    return api.create_user(api.UserCreate(username=username, real_name=real_name, role=role))


def ensure_quest(title: str, creator_id: int, description: str) -> api.models.Quest:
    """Create a quest if a matching one does not already exist."""
    cur = api.conn.cursor()
    cur.execute("SELECT id FROM quests WHERE title=? AND creator_id=?", (title, creator_id))
    row = cur.fetchone()
    if row:
        return api.get_quest_by_id(row[0])
    return api.create_quest(api.QuestCreate(title=title, description=description, reward=0, creator_id=creator_id))


def main():
    db_path = os.environ.get("BOARD_DB_PATH", api.DB_PATH)
    print(f"Seeding tasks using database at {db_path}")

    # Create initial users representing the core team
    admin = ensure_user("admin", "CivicForge Admin", "Organizer")
    dev = ensure_user("dev", "Core Developer", "Participant")

    # Outstanding tasks from mvp_board_plan.md
    ensure_quest(
        "Migrate project tracking to the Board",
        admin.id,
        "Start using the MVP board for tracking development tasks and feedback.",
    )
    ensure_quest(
        "Implement Forge API stubs",
        admin.id,
        "Add placeholder endpoints for identity verification and board/feature registration.",
    )

    print("Seeding complete.")


if __name__ == "__main__":
    main()
