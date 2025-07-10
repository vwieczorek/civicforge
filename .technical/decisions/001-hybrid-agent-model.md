# ADR-001: Hybrid Agent Model for Privacy and Power

## Status
Accepted

## Context
Building AI-powered civic engagement faces a fundamental tension: powerful AI requires data and compute that threatens user privacy. Traditional approaches either sacrifice capability (fully local) or privacy (fully cloud).

## Decision
We will implement a Hybrid Agent Model that splits AI functionality between:
- **Local Controller**: On-device component that owns identity, enforces consent, and guards privacy
- **Remote Thinker**: Cloud component that provides intelligence without accessing private data

All interactions between components require explicit user consent.

## Consequences

### Positive
- User data never leaves device without explicit permission
- Users maintain sovereignty over AI actions
- Can leverage powerful cloud AI while preserving privacy
- Clear security boundary between components

### Negative
- Increased system complexity
- Potential latency from consent flows
- Requires careful API design to minimize data sharing
- More difficult to implement than monolithic approach

### Mitigation
- Design streamlined consent UX to minimize friction
- Implement smart batching for related actions
- Use progressive disclosure to share minimum required data