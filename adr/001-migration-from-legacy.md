# ADR-001: Migration to New Repository

## Status
Accepted

## Context
The original civicforge repository accumulated technical debt from multiple architectural pivots:
- Mixed PostgreSQL and serverless implementations
- 158 files with 40k+ lines of code
- Exposed AWS infrastructure endpoints in git history
- Multiple competing documentation visions
- Complex nested structures obscuring the core mission

## Decision
We will create a new `civicforge-serverless` repository containing only the essential serverless implementation, while archiving the original repository for historical reference.

This follows the "Living Archive" approach:
1. Create clean repository with only essential code
2. Archive original repository as read-only reference
3. Link between them for historical context

## Consequences

### Positive
- Clean git history from day one (no exposed secrets)
- Focused codebase aligned with dual-attestation mission
- Dramatically simplified onboarding (target: 30 minutes)
- Clear, minimal documentation (<500 lines total)
- Forces conscious decisions about what is truly essential

### Negative
- Loss of detailed commit history (mitigated by archive access)
- All developers must update their remotes
- Open PRs and issues need manual migration
- Some context may be lost in translation

### Neutral
- Approximately 50 files vs 158 in original
- New repo structure optimized for serverless-first approach

## Implementation
See FRESH_START_MIGRATION_PLAN.md in the original repository for detailed steps.

Date: January 10, 2025
Author: CivicForge Team