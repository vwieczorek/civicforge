# CLAUDE.md - CivicForge Development Guide

Essential context for AI agents working on CivicForge.

## What is CivicForge?

A conversation-driven platform for civic engagement where AI acts as a "Civic Compass" - guiding citizens to discover and coordinate community participation while maintaining human control.

## Top Priority Architecture (Focus Here)

### 1. Hybrid Agent Model ⭐⭐⭐⭐⭐
The core innovation - splitting AI functionality between:
- **Local Controller**: On-device app managing identity, values, and approval
- **Remote Thinker**: Cloud AI for understanding, discovery, and coordination

This is THE fundamental architectural decision. All other features build on this foundation.

### 2. Decentralized Identity (W3C DIDs) ⭐⭐⭐⭐⭐
- Self-sovereign identity without central authority
- Verifiable Credentials for permissions
- Critical for trust without centralization

### 3. Federated P2P Network ⭐⭐⭐⭐⭐
- Community Hubs run by local organizations
- Peer-to-peer discovery protocols
- No single point of failure

### 4. Natural Language Interface ⭐⭐⭐⭐⭐
- Citizens interact through conversation, not forms
- AI understands intent and context
- Makes civic engagement accessible to all

## Key Design Principles

1. **Humans navigate, AI guides** - Like a compass showing direction
2. **Privacy by design** - Local processing, cryptographic guarantees
3. **Community ownership** - Federated, not centralized
4. **Explicit consent** - Nothing happens without user approval

## Novel Features (Important but Secondary)

- **Serendipity Slider** - Adjust how unexpected suggestions are
- **Non-fungible Reputation** - Context-specific, can't be traded
- **Privacy Budget** - Prevents user profiling
- **Emotion Preservation** - AI won't mediate emotional support

## Technical Stack

**Priority Components:**
- Local Controller: React Native + DID:web
- Remote Thinker: Python + LLMs
- Network: libp2p + Community Hubs
- Identity: W3C DID standards

**Supporting Tech** (mentioned for completeness):
- Storage: IPFS, Vector DBs
- Discovery: Kademlia DHT
- Signatures: EIP-712

## Current Status

**Phase 1 Implementation**: Building core NLP for natural language understanding
- ✅ Intent recognition (OFFER_HELP, REQUEST_HELP, SHARE_AVAILABILITY, SHARE_SKILLS)
- 🚧 Entity extraction, dialog management, context tracking

## Implementation Approach

We're starting simple to validate the core concept, then building towards the full vision:
1. **Now**: Basic NLP + simple client-server to prove conversational civic engagement works
2. **Next**: Add Local Controller for privacy/consent
3. **Then**: Implement DIDs and federated architecture
4. **Future**: Full P2P network with Community Hubs

## For Contributors

**Immediate focus**: Natural language understanding and conversation engine
**Vision focus**: Keep the Hybrid Agent Model, DIDs, and federation in mind for all design decisions

## Quick Reference

- Implementation: `./src/`
- Documentation: `./docs/`
- Working demo: `./try-it/`
- Vision details: `./docs/vision.md`
- Technical roadmap: `./docs/technical/`

Remember: This is about amplifying human civic engagement, not replacing it. The technology serves the community, not the other way around.