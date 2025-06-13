# Legacy Test Refactoring Plan

## Decision: Refactor, Don't Remove

After analysis, we've determined that the failing legacy tests contain valuable test cases mixed with low-quality ones. Rather than removing them, we'll refactor to preserve the value.

## Current State
- 12 failing tests in legacy files
- Mix of import errors, mock issues, and incorrect assertions
- Valuable business logic tests buried in poorly organized files

## Refactoring Plan

### Phase 1: Quick Fixes (Immediate)
- [x] Created `test_unit_fixed.py` with high-value tests extracted
- [ ] Fix import paths: `from models` → `from src.models`
- [ ] Comment out or skip truly broken tests

### Phase 2: Reorganization (Next Sprint)
Create focused test modules:
- `test_state_machine.py` - Quest lifecycle tests
- `test_signature.py` - Cryptographic verification tests  
- `test_feature_flags.py` - Feature flag tests
- `test_auth.py` - Authentication tests (with proper RSA mocks)

### Phase 3: Cleanup (Future)
- Remove low-value tests (Pydantic validation, enum tests)
- Remove tests for private implementation details
- Update test assertions to match actual behavior

## Tests to Remove
- `test_quest_create_validation` - Tests Pydantic itself
- `test_quest_submission_validation` - Tests Pydantic itself
- `test_models_enum_values` - Tests Python enums
- `test_db_serialization` - Implementation detail, covered by integration tests

## Tests to Fix and Keep
- All `QuestStateMachine` tests - Core business logic
- All signature verification tests - Security critical
- Feature flag tests - Important for rollouts
- Auth tests - Need proper RSA keypair mocks

## Why Keep Legacy Tests?
1. **Historical Context**: Show how the codebase evolved
2. **Hidden Value**: Some tests cover edge cases not in newer tests
3. **Refactoring Safety**: Better to fix than risk losing coverage
4. **Technical Debt Record**: Documents areas needing improvement

## Next Steps
1. Use `test_unit_fixed.py` for immediate needs
2. Gradually migrate tests to focused modules
3. Delete only after confirming coverage elsewhere
4. Update this plan as refactoring progresses