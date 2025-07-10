# CivicForge Core Implementation

This directory contains the core implementation of CivicForge's conversational civic engagement platform.

## Quick Start

1. **Install dependencies:**
   ```bash
   cd src
   pip install -r requirements-dev.txt
   ```

2. **Run the API server:**
   ```bash
   python run_api.py
   ```

3. **Try the demo:**
   ```bash
   python examples/api_demo.py
   ```

4. **Explore the API:**
   - Interactive docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## Project Structure

```
src/
├── core/                    # Core business logic
│   ├── conversation/        # Dialog management
│   ├── nlp/                # Natural language processing
│   ├── matching/           # Volunteer-opportunity matching
│   └── interfaces/         # Privacy, consent, local controller
├── api/                    # REST API endpoints
├── examples/               # Usage examples
└── run_api.py             # API server runner
```

## Key Features Implemented

### ✅ Phase 1 Complete
- **Natural Language Understanding**: Intent recognition and entity extraction
- **Conversation Management**: State-based dialog flow
- **Matching Engine**: Skills-based volunteer-opportunity matching
- **API Layer**: RESTful endpoints for all functionality

### 🔧 Mock Implementations (Ready for Phase 2)
- **Local Controller**: Interface defined, mock implementation
- **Privacy Manager**: Privacy budget concept implemented
- **Consent Manager**: Explicit consent framework

## API Endpoints

### Conversation
- `POST /api/conversation` - Process a conversation turn
- `GET /api/conversation/{session_id}/summary` - Get conversation summary
- `POST /api/conversation/{session_id}/reset` - Reset conversation

### Opportunities
- `POST /api/opportunities` - Create opportunity
- `GET /api/opportunities` - List opportunities
- `GET /api/opportunities/{id}` - Get specific opportunity

### Volunteers
- `POST /api/volunteers` - Create/update volunteer profile
- `GET /api/volunteers/{user_id}` - Get volunteer profile

### Matching
- `POST /api/matches` - Find matches for a volunteer

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest core/matching/tests/test_opportunity_matcher.py

# Run with coverage
pytest --cov=core --cov-report=html
```

## Next Steps

1. **Implement persistence layer** - Replace in-memory storage with database
2. **Build Local Controller** - Create real approval UI (React Native)
3. **Add real DIDs** - Implement W3C DID standards
4. **Deploy Community Hubs** - Begin federation architecture

## Development Guidelines

- Follow test-driven development
- Use type hints for all functions
- Document all public APIs
- Keep privacy-first principles
- Ensure explicit consent flows

## Vision Alignment

This implementation follows CivicForge's core principles:
- **Humans navigate, AI guides**: Conversational interface assists, doesn't decide
- **Privacy by design**: Privacy budget and consent built into core
- **Community ownership**: Ready for federated deployment
- **Explicit consent**: Nothing happens without user approval

See `/docs/vision.md` for complete vision and `CLAUDE.md` for development context.