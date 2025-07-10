# CivicForge: Your Civic Compass

> Human-amplified civic engagement through conversational AI

## Overview

CivicForge transforms civic participation through natural conversation. Instead of navigating complex websites, citizens simply talk with their Civic Compass - an AI assistant that helps discover opportunities, coordinate with neighbors, and amplify community impact while keeping humans in control.

## Core Architecture: The Hybrid Agent Model

The foundation of CivicForge is a carefully balanced split between local control and intelligent assistance:

### Local Controller (Your Device)
- **Holds your identity keys** - Only you control your civic identity (W3C DIDs)
- **Stores your values** - Your "Personal Constitution" guides all AI recommendations  
- **Final approval authority** - Nothing happens without your explicit consent
- **Privacy guardian** - Sensitive data never leaves your device
- **Works offline** - Queues actions when disconnected, syncs when ready

### Remote Thinker (Cloud/Edge)
- **Natural language understanding** - Interprets your civic needs from conversation
- **Opportunity discovery** - Finds relevant ways to help based on your interests
- **Coordination assistance** - Negotiates with other agents to reduce friction
- **Context-aware guidance** - Learns your patterns while respecting privacy boundaries

This separation ensures you maintain sovereignty while benefiting from powerful AI capabilities.

## Federated P2P Network

Unlike centralized platforms, CivicForge operates through community-owned infrastructure:

- **Community Hubs** - Run by local governments, nonprofits, or trusted organizations
- **Resilient connectivity** - Works even with intermittent internet through store-and-forward
- **Peer-to-peer discovery** - Find opportunities without exposing your data
- **No single point of failure** - Network continues even if individual nodes go down
- **Local governance** - Communities control their own civic data

## Trust Through Decentralized Identity

Every participant has a verifiable identity without centralized control:

- **W3C DIDs** - Self-sovereign identity you own
- **Verifiable Credentials** - Prove civic contributions cryptographically
- **Composite Reputation** - Combines human actions with AI behavior
- **Privacy-preserving** - Share only what's needed, when needed

## Natural Language Interface

Civic engagement becomes as simple as having a conversation:

```
You: "I have two hours free this weekend and want to help"

Civic Compass: "I found three opportunities nearby:
- Beach cleanup Saturday morning (1.5 hours)
- Food bank needs drivers (2 hour shifts)
- Library seeks reading volunteers (flexible)

The beach cleanup matches your environmental interests. Should I connect you with the organizer?"
```

## Key Innovations

- **Serendipity Slider** - Discover unexpected ways to contribute
- **Non-fungible Reputation** - Context-specific trust that can't be gamed
- **Privacy Budget** - Limits queries to prevent profiling
- **Emotion Preservation** - AI never mediates human emotional support

## Getting Started

### Try the Prototype

We have a working prototype! See [prototype/README.md](./prototype/README.md) to run the basic Local Controller and Remote Thinker demo.

### Learn More

1. Review [Vision Document](./civic-compass-vision/CIVIC_COMPASS_CIVICFORGE_VISION.md)
2. Explore [Technical Architecture](./civic-compass-vision/CIVIC_COMPASS_TECHNICAL_SPEC.md)  
3. Check our [Roadmap](./ROADMAP.md) for development plans
4. See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines

## Security & Privacy

Built on privacy-first principles:
- Local processing when possible
- Cryptographic guarantees
- User-controlled data
- See [SECURITY.md](./SECURITY.md) for details

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](./LICENSE) file for details.