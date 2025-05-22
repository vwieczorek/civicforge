# Board MVP Schema

This directory contains a minimal Python module defining the initial database schema for the first CivicForge Board.

Run the module as a script to create an SQLite database named `board.db` in the current directory:

```bash
python models.py
```

The schema defines tables for:

- **users** – account details and reputation
- **quests** – work items tracked through their lifecycle
- **verifications** – dual-attestation records for quest completion
- **experience_ledger** – experience point transactions

These tables are a foundation for implementing the quest state machine and reputation system described in `mvp_board_plan.md`.

## Running the API and Web UI

To start the combined API and web interface:

```bash
uvicorn board_mvp.web:app --reload
```

This serves the API under `/api` and a very small HTML interface at `/` for listing
and creating quests.
