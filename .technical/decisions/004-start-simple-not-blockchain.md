# ADR-004: Start Simple, Not Blockchain

## Status
Accepted

## Context

The civic tech landscape is littered with failed projects that prioritized technical sophistication over user value. After studying successful platforms and analyzing why others failed, we face a critical architectural decision: should we build the full decentralized architecture from day one, or start simple and evolve?

Many well-funded civic tech initiatives have failed by assuming that people desperately want new tools for civic engagement. They built complex platforms with blockchain, decentralized identity, and peer-to-peer networking before validating that anyone wanted to use them.

## Decision

We will build CivicForge using conventional client-server architecture first, deferring all blockchain, DID, and P2P complexity until we have proven user demand and specific needs that require decentralization.

Phase 1 implementation:
- Standard mobile/web application (the "Local Controller")
- Traditional backend API (the "Remote Thinker")  
- PostgreSQL database for data storage
- Standard authentication (OAuth/JWT)
- HTTPS for all communications

The principles of user control, privacy, and consent will be implemented through:
- Clear data permissions in the UI
- Explicit user approval for all actions
- Local data storage where practical
- Strong encryption for sensitive data

## Consequences

### Positive
- **Faster Time to Value**: Launch in months, not years
- **Lower Barrier to Entry**: Standard tech stack that any developer knows
- **Rapid Iteration**: Learn what users actually want before architecting for it
- **Reduced Complexity**: Focus engineering effort on user experience, not infrastructure
- **Proven Path**: Follow successful platforms that started simple

### Negative  
- **Technical Debt**: May need to migrate later if decentralization becomes necessary
- **Limited Features**: Can't claim true decentralization or censorship resistance initially
- **Perception Risk**: Some may see us as "just another app"

### Mitigations
- Design APIs and data models to be migration-friendly
- Be transparent about our roadmap and philosophy
- Demonstrate value through results, not architecture
- Keep the door open for future decentralization when needed

## Alternatives Considered

1. **Full Blockchain First**: Build complete decentralized system from day one
   - Rejected: Too complex, too slow, unproven need

2. **Hybrid Approach**: Some decentralization, some centralization
   - Rejected: Worst of both worlds - still complex but not fully decentralized

3. **Use Existing Blockchain**: Build on Ethereum, Solana, etc.
   - Rejected: Adds complexity and cost without clear user benefit

## References

- Civic tech failure analysis showing complexity as a key failure factor
- Successful platforms (Facebook, Twitter, etc.) that started centralized
- "Premature optimization is the root of all evil" - Donald Knuth
- Lean Startup principles: Build, Measure, Learn

## Review

This decision will be reviewed after:
- 1,000 active users
- 6 months of operation  
- First community crisis response
- Clear user demand for features requiring decentralization

At that point, we will assess whether the benefits of decentralization outweigh the costs and complexity for our specific use case.