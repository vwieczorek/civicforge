# First Board MVP Plan (Updated May 24, 2025)
*Based on `math_model_guidance.md` and current implementation status*

## 🚀 Current Status for Next Developer

### What's Working Now
- ✅ **Full quest lifecycle** with XP economy
- ✅ **Web UI** at http://localhost:8000 (run: `uvicorn src.board_mvp.web:app --reload`)
- ✅ **Quest categories** with filtering
- ✅ **Stats dashboard** showing board metrics
- ✅ **XP spending** for quest creation (5 XP) and boosting (10 XP)
- ✅ **Database migrations** script for schema updates

### Next Priority: Authentication
The system is functional but **NOT SECURE**. The next critical step is implementing basic authentication to protect the platform before any real usage.

### Known Issues
- ⚠️ SQLite threading fixed with thread-local connections
- ⚠️ Deprecation warnings for datetime.utcnow() (non-critical)
- ⚠️ No authentication - anyone can perform any action

## 1. Core Goals ✅
- ✅ Deliver a working Board where users can create, claim, verify, and log Quests
- ✅ Introduce Experience points and a simple reputation system
- 🔄 Provide stubs for Forge-level interactions (identity, governance, feature registry)
- 🎯 Move CivicForge development tracking to this Board ASAP to validate usefulness

## 2. Current Implementation Status

### ✅ Completed Features

#### 2.1 User Identity and Accounts
- Basic user model with username, real_name, role
- `verified` flag for future KYC integration
- Roles: Organizer, Participant (Verifier role implicit)

#### 2.2 Quest Lifecycle
- Full state machine (S0–S12) implemented
- Create → Claim → Verify → Log flow working
- EXCEPTIONAL completion with bonus rewards
- Dual-attestation between performer and verifier

#### 2.3 Verification & Reputation
- Basic reputation system implemented
- Reputation increases on successful verification
- Reputation decreases on failed work
- Updates for both performers and verifiers

#### 2.4 Experience Points (Partial)
- Experience ledger tracking all transactions
- Rewards: Normal (10), Exceptional (20), Verifier (5/10)
- Weekly decay mechanism via `run_decay` command
- ❌ Cannot spend Experience yet (no quest creation costs)

#### 2.5 Basic Web UI & CLI
- Web interface for quest lifecycle
- CLI for all operations
- Form-based interaction (no auth yet)

### ✅ Recently Completed (May 24, 2025)

#### 2.6 Experience Spending
- ✅ Quest creation costs (5 XP)
- ✅ Quest boosting mechanism (10 XP, increases boost_level)
- ✅ XP balance checking and enforcement
- ❌ Additional experience-based privileges

#### 2.7 Quest Categorization
- ✅ Category field added to quests
- ✅ Categories: civic, environmental, social, educational, technical, general
- ✅ Category filtering in UI and API
- ✅ Category-based statistics

#### 2.8 Stats and Impact
- ✅ StatsBoard API endpoints (/api/stats/board, /api/stats/user/{id})
- ✅ Board-wide metrics collection
- ✅ Simple dashboard view at /stats
- ❌ Composite Community Impact Index (CCII)
- ❌ Export capability for analysis

### ❌ Not Yet Implemented

#### 2.9 Moderation & Disputes
- Dispute resolution beyond states
- Board-level moderation tools
- Escalation to Forge council

#### 2.9 Forge Integration
- Global identity verification (`U_global`)
- Board registration API
- Feature registry (`F_registry`)
- Cross-board collaboration (`X_global`)

## 3. Immediate Priorities (Next 2-4 Weeks)

### Phase 1: Production Readiness & Dogfooding
1. **Deploy the MVP**
   - [ ] Switch to PostgreSQL for thread safety
   - [ ] Deploy to AWS (Lambda + RDS)
   - [ ] Set up basic monitoring/logging
   - [ ] Automate weekly decay with cron/CloudWatch

2. **Start Using It**
   - [x] Run `seed_tasks.py` to populate initial quests ✅
   - [x] Fixed SQLite threading issues for web deployment ✅
   - [ ] Create quests for remaining CivicForge work
   - [ ] Complete and verify at least 10 real tasks
   - [ ] Document pain points and UX issues

3. **Basic Authentication** ⚠️ HIGH PRIORITY - Next Step
   - [ ] Add email/password auth to web UI
   - [ ] Protect quest creation/claiming/verification
   - [ ] Add session management
   - [ ] Basic "forgot password" flow

### Phase 2: Core Mechanics Completion ✅ MOSTLY COMPLETE

4. **Experience Point Spending** ✅ IMPLEMENTED
   - [x] Quest creation costs 5 XP
   - [x] Quest boosting costs 10 XP
   - [x] Balance checking prevents overspending
   - [x] Initial XP grants in seed script

5. **Quest Categorization** ✅ IMPLEMENTED
   - [x] Added `category` field to quests table
   - [x] Categories: civic, environmental, social, educational, technical, general
   - [x] Category filtering in UI and API
   - [x] Category-based statistics

6. **Basic StatsBoard** ✅ IMPLEMENTED
   - [x] API endpoints: `/api/stats/board` and `/api/stats/user/{id}`
   - [x] Tracks: quests by status/category, XP circulation, active users
   - [x] Dashboard view at `/stats`
   - [ ] Export capability for analysis

### Phase 3: Federation Foundation (Weeks 5-8)

7. **Forge API Stubs**
   ```python
   # forge_stubs.py
   class ForgeAPI:
       def verify_identity(self, user_data):
           """Mock U_global verification"""
           return {"verified": True, "global_id": "mock_123"}
       
       def register_board(self, board_config):
           """Register board with Forge"""
           return {"board_id": "board_001", "status": "registered"}
       
       def get_feature_registry(self):
           """Return available features/themes"""
           return {"features": ["basic_quests", "reputation_v1"]}
   ```

8. **Board Configuration (`Conf_Board`)**
   - [ ] Add `board_config` table
   - [ ] Configurable: theme, rules, quest types, XP rates
   - [ ] UI for board administrators
   - [ ] Export/import config for sharing

9. **Cross-Board Quest Visibility**
   - [ ] Add `visibility` field to quests (board-only, federated)
   - [ ] API to list federated quests from other boards
   - [ ] Basic cross-board quest claiming (with home board XP)

## 4. Architecture Updates

### Database Migrations Needed
```sql
-- Add missing fields
ALTER TABLE quests ADD COLUMN category VARCHAR(50);
ALTER TABLE quests ADD COLUMN visibility VARCHAR(20) DEFAULT 'board';
ALTER TABLE quests ADD COLUMN boost_level INTEGER DEFAULT 0;

-- Board configuration
CREATE TABLE board_config (
    id INTEGER PRIMARY KEY,
    board_id VARCHAR(50) UNIQUE,
    name VARCHAR(100),
    theme JSON,
    rules JSON,
    xp_rates JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Quest costs tracking
ALTER TABLE experience_ledger ADD COLUMN quest_cost_type VARCHAR(20);
```

### API Endpoints to Add
- `POST /api/quests/{id}/boost` - Boost quest visibility
- `GET /api/stats/board` - Board-wide statistics
- `GET /api/stats/user/{id}` - User statistics
- `POST /api/forge/verify-identity` - Stub for U_global
- `POST /api/forge/register-board` - Register with Forge
- `GET /api/forge/features` - Get F_registry

## 5. Testing & Validation Plan

### Dogfooding Metrics
- [ ] Track time from quest creation to completion
- [ ] Measure verification turnaround time
- [ ] Count dispute rate (even if not resolved yet)
- [ ] Survey users on XP earning satisfaction
- [ ] Document all UX friction points

### Integration Tests to Add
- [ ] Test XP spending and balance enforcement
- [ ] Test concurrent quest claims
- [ ] Test reputation calculation accuracy
- [ ] Test cross-board quest visibility (once implemented)

## 6. Migration Path

### From MVP to Multi-Board Federation
1. **Single Board** (current) → Test all mechanics
2. **Board + Forge Stubs** → Define integration points
3. **Two Boards + Real Forge** → Test federation
4. **N Boards + Governance** → Full platform

### Data Migration Considerations
- User IDs will map to U_global when Forge is ready
- Local XP will become board-specific XP
- Reputation will have board and global components
- Quest IDs will need board prefixes

## 7. Risk Mitigation

### Technical Risks
- **SQLite in production**: Move to PostgreSQL before any real usage
- **No auth**: Add immediately after initial testing
- **Manual processes**: Automate decay, stats collection
- **No backups**: Implement before going live

### Community Risks
- **Gaming the system**: Monitor for suspiciously fast quest completion
- **Collusion**: Track performer-verifier pairs for patterns
- **Low engagement**: Make initial quests compelling and varied
- **Disputes**: Have manual resolution ready even without full system

## 8. Success Criteria for MVP

### Week 2
- [ ] 5+ real CivicForge development quests completed
- [ ] 3+ contributors using the system
- [ ] Basic auth protecting the system
- [ ] Deployed to cloud (not local SQLite)

### Week 4
- [ ] 20+ quests completed
- [ ] XP spending implemented
- [ ] Basic stats dashboard live
- [ ] First cross-board quest attempted

### Week 8
- [ ] 2 boards running independently
- [ ] Forge stubs handling identity/registration
- [ ] 50+ quests across both boards
- [ ] Community feedback incorporated
- [ ] Clear path to full federation

## 9. Next Immediate Actions

1. **Today**: Deploy to AWS with PostgreSQL
2. **Tomorrow**: Run seed_tasks.py and create 5 real quests
3. **This Week**: Add basic auth and XP spending
4. **Next Week**: Implement StatsBoard and start measuring impact

---

*Remember: The goal is a working system that proves the model. Perfect is the enemy of good. Ship, learn, iterate.*