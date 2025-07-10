# ADR-003: Privacy-Preserving Architecture

## Status
Accepted

## Context
Civic engagement platforms typically become surveillance systems, profiling users to "improve matching." This violates user privacy and creates honeypots for adversaries.

## Decision
Implement Privacy by Design through:
- **Local-first processing**: Sensitive operations on user device
- **Privacy Budget**: Quantifiable privacy spending
- **Fuzzy Data**: Location/time generalization
- **Progressive Disclosure**: Share minimum required
- **Zero-Knowledge Proofs**: Future verification without revelation

## Consequences

### Positive
- Users control their data disclosure
- No central profiling database
- Privacy becomes tangible via budgets
- Resistant to surveillance capitalism
- Regulatory compliance (GDPR, etc.)

### Negative
- Advanced privacy tech (homomorphic encryption) not yet performant
- More complex than traditional architectures
- May limit some matching capabilities
- Requires user education

### Mitigation
- Start with conventional privacy techniques
- Research and prototype advanced methods separately
- Design for progressive privacy enhancement
- Clear UI showing privacy implications