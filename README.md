# civicforge-serverless

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-85%25-green)
![License](https://img.shields.io/badge/license-MIT-blue)

**Enabling peer-to-peer trust through dual-attestation of community quests.**

## What is this?

This repository contains the serverless backend and frontend for CivicForge. It manages user identities, quest definitions, and the cryptographic attestations that form the basis of our trust network. When community members complete tasks (quests), both the requestor and performer must attest to successful completion, creating a decentralized verification system.

## Core Concepts

- **Quests:** Community-defined tasks that need completion
- **Attestations:** Verifiable claims made by users about quest completion
- **Dual-Attestation:** Our core security model requiring both parties to verify

## Prerequisites

- Node.js (v18+)
- pnpm
- AWS CLI (configured)
- Docker (for local DynamoDB)

## Quick Start

```bash
# Clone and install
git clone https://github.com/civicforge/civicforge-serverless
cd civicforge-serverless
pnpm install

# Configure environment
cp .env.example .env
# Edit .env with your AWS credentials

# Run locally
pnpm run dev

# Frontend will be at http://localhost:3000
# API will be at http://localhost:3001
```

## Project Structure

- `README.md` - You are here
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) - System design and core principles
- [`DEVELOPMENT.md`](./DEVELOPMENT.md) - Detailed setup and contribution guide
- [`OPERATIONS.md`](./OPERATIONS.md) - Deployment and monitoring
- [API Documentation](https://api.civicforge.org/docs) - Auto-generated from OpenAPI spec

## License

MIT - See [LICENSE](./LICENSE) for details