# Board MVP - CivicForge Board Implementation

This is the Minimum Viable Product implementation of a CivicForge Board - a local task/quest management system with reputation and experience points.

## Quick Start

```bash
# From the project root, initialize the database
python -m src.board_mvp.models

# Run the web interface (API + UI)
uvicorn src.board_mvp.web:app --reload
# Visit http://localhost:8000

# Or use the CLI
python -m src.board_mvp.cli --help

# Seed with development tasks
python -m src.board_mvp.seed_tasks
```

## Components

The schema defines tables for:

- **users** – account details and reputation
- **quests** – work items tracked through their lifecycle
- **verifications** – dual-attestation records for quest completion
- **experience_ledger** – experience point transactions

These tables implement the quest state machine and reputation system described in `docs/technical/mvp_board_plan.md`.

## Features

### ✅ Implemented
- User accounts with roles (Organizer, Participant)
- Full quest lifecycle (Create → Claim → Verify → Complete)
- Dual-attestation between performer and verifier
- Experience points with rewards and weekly decay
- Basic reputation tracking
- Web UI and CLI interfaces

### ❌ Not Yet Implemented
- Experience spending (quest creation costs)
- Quest boosting
- Dispute resolution
- Board customization
- Federation with other boards

## API Endpoints

The API is served under `/api` with these main endpoints:
- `GET /api/users` - List all users
- `POST /api/users` - Create a new user
- `GET /api/quests` - List all quests
- `POST /api/quests` - Create a new quest
- `POST /api/quests/{id}/claim` - Claim a quest
- `POST /api/quests/{id}/verify` - Verify quest completion
- `GET /api/experience/{user_id}` - Get user's experience balance

## Development

Run tests:
```bash
python -m pytest src/board_mvp/tests/
```

The quest state machine follows the flow defined in the mathematical model, with states S0-S12 representing the full lifecycle from creation to completion or cancellation.
