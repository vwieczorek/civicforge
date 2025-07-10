# ADR-002: Federated P2P Network Over Pure Decentralization

## Status
Accepted

## Context
Pure decentralization (like blockchain) promises no single point of failure but introduces complexity, performance issues, and governance challenges. Pure centralization creates platform lock-in and surveillance risks.

## Decision
Implement a Federated P2P Network where:
- Community organizations run "Community Hubs"
- Hubs federate to share opportunities
- Users choose their trusted hub
- P2P protocols enable direct agent communication
- No blockchain or consensus requirements

## Consequences

### Positive
- Communities maintain control of their infrastructure
- Performance suitable for real-time interaction
- Progressive decentralization path
- Familiar governance model (organizations run hubs)
- Resilient to single points of failure

### Negative
- Not fully decentralized from day one
- Requires trust in hub operators
- Potential for hub fragmentation
- More complex than pure client-server

### Mitigation
- Start with REST APIs, evolve to P2P
- Publish hub operation standards
- Enable hub migration for users
- Design for hub interoperability from start