# CivicForge Source Code

This directory contains the implementation of CivicForge components.

## Current Components

### board_mvp/
The Minimum Viable Product (MVP) implementation of a CivicForge Board.

**Key Files:**
- `models.py` - Database models (User, Quest, Verification, Experience)
- `api.py` - FastAPI REST endpoints
- `web.py` - Web interface (combines API + simple HTML UI)
- `cli.py` - Command-line interface for all operations
- `seed_tasks.py` - Populate board with initial development tasks
- `tests/` - Test suite

**Current Features:**
✅ User accounts with roles (Organizer, Participant)
✅ Quest lifecycle (Create → Claim → Verify → Complete)
✅ Dual-attestation verification
✅ Experience points with weekly decay
✅ Basic reputation system
❌ Experience spending (quest creation costs)
❌ Dispute resolution
❌ Federation with other boards

**Running the MVP:**
```bash
# Install dependencies
pip install fastapi uvicorn typer rich

# Initialize database
python -m src.board_mvp.models

# Run web interface
uvicorn src.board_mvp.web:app --reload

# Use CLI
python -m src.board_mvp.cli --help

# Seed with sample data
python -m src.board_mvp.seed_tasks
```

## Future Components

### forge/ (planned)
Global governance layer managing:
- User identity verification (U_global)
- Board registration and discovery
- Feature registry (F_registry)
- Cross-board collaboration protocols
- Dispute escalation

### shared/ (planned)
Shared utilities and libraries:
- Authentication/authorization
- Common data models
- API clients
- Monitoring and metrics

## Development Guidelines

1. Start simple, iterate based on real usage
2. Prioritize working code over perfect architecture
3. Test with real community tasks ASAP
4. Document pain points for future improvements