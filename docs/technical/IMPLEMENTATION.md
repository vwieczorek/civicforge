# Implementation Guide

*For developers ready to build CivicForge*

## Start Here

The vision is clear: conversational AI for civic engagement. This guide shows how to build it methodically.

## Current State

- **Vision**: Complete ✓
- **Prototype**: Demo concept in `try-it/` ✓
- **Implementation**: Starting fresh in `src/` ←You are here

## Implementation Phases

### Phase 1: Core Conversation Engine (Weeks 1-4)

**Goal**: Real natural language understanding replacing keyword matching

```
src/
├── core/
│   ├── nlp/
│   │   ├── intent_recognition.py
│   │   ├── entity_extraction.py
│   │   └── tests/
│   ├── conversation/
│   │   ├── dialog_manager.py
│   │   ├── context_tracker.py
│   │   └── tests/
│   └── matching/
│       ├── opportunity_matcher.py
│       ├── skill_analyzer.py
│       └── tests/
```

**First PR Goal**: User says "I want to help" → System understands intent

**Tests First**:
```python
def test_basic_help_intent():
    """User expresses desire to help"""
    response = nlp.parse("I want to help my community")
    assert response.intent == "OFFER_HELP"
    assert response.confidence > 0.8
```

### Phase 2: Local Controller App (Weeks 5-8)

**Goal**: Mobile app that guards privacy and approvals

```
src/
├── app/
│   ├── ios/
│   ├── android/
│   ├── shared/
│   │   ├── components/
│   │   ├── stores/
│   │   └── tests/
```

**First PR Goal**: Display conversation and approval UI

**Tests First**:
```typescript
test('approval flow shows clear action', () => {
  const action: ApprovalAction = {type: 'CONNECT', with: 'Community Garden'};
  const component = render(<ApprovalDialog action={action} />);
  expect(component.getByText('Connect with Community Garden?')).toBeVisible();
});
```

### Phase 3: Opportunity Management (Weeks 9-12)

**Goal**: Real opportunities from real organizations

```
src/
├── backend/
│   ├── api/
│   │   ├── opportunities.py
│   │   ├── organizations.py
│   │   └── tests/
│   ├── db/
│   │   ├── models.py
│   │   ├── migrations/
│   │   └── tests/
```

**First PR Goal**: Organization can post "need help with X"

**Tests First**:
```python
def test_create_opportunity():
    """Organization creates opportunity"""
    opp = Opportunity.create(
        title="Garden Volunteers Needed",
        when="Saturday mornings",
        skills=["gardening", "outdoor work"]
    )
    assert opp.is_active
    assert "gardening" in opp.skills
```

### Phase 4: Privacy Layer (Weeks 13-16)

**Goal**: Implement privacy promises from vision

```
src/
├── privacy/
│   ├── consent_manager.py
│   ├── data_minimizer.py
│   ├── local_storage.py
│   └── tests/
```

**First PR Goal**: Nothing shared without explicit consent

**Tests First**:
```python
def test_no_sharing_without_consent():
    """Verify data stays local until approved"""
    user_data = {"name": "Sarah", "interests": ["gardening"]}
    shared = privacy.get_shareable_data(user_data, consent=None)
    assert shared == {}
```

## Development Principles

### 1. Test-Driven Development
- Write test first
- Make it pass
- Refactor
- Every PR must increase test coverage

### 2. User-Facing Features First
- Can a user see/experience this change?
- If no, is it necessary for next user feature?
- Technical perfection can wait

### 3. Real Data Early
- Connect with 1 real organization by Week 4
- Test with 10 real users by Week 8
- Measure actual connections made

### 4. Simple Deployment
- `make test` - Run all tests
- `make run` - Start locally
- `make deploy` - Ship to staging
- No complex configs

## Success Metrics

Track these from Day 1:

1. **Conversation Success Rate**: % of inputs understood correctly
2. **Time to First Connection**: How fast user gets matched
3. **Approval Rate**: % of suggested connections approved
4. **Actual Connections**: Real people meeting in real life

## Getting Started Checklist

- [ ] Clone repo and run prototype (`try-it/demo.sh`)
- [ ] Read vision docs to understand why we're building
- [ ] Set up development environment (see below)
- [ ] Pick first test from Phase 1
- [ ] Make it pass
- [ ] Submit PR

## Development Setup

```bash
# Backend (Python)
cd src
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Frontend (TypeScript + React Native)
cd src/app
npm install

# Run tests
make test

# Start development
make dev
```

## Questions?

- **Technical**: Create GitHub issue
- **Vision**: Read `docs/vision.md`
- **Architecture**: See `.technical/decisions/`

Remember: We're building for humans. Every line of code should make someone's life better.

---

*Make it work. Make it right. Make it fast. In that order.*
