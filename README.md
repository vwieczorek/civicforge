# civicforge-serverless

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-30%25-orange)
![License](https://img.shields.io/badge/license-MIT-blue)
![Deployment](https://img.shields.io/badge/deployment-mvp_ready-green)

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
npm install

# Configure environment
cp frontend/.env.example frontend/.env
# Edit frontend/.env with your Cognito configuration

# Run locally
npm run dev

# Frontend will be at http://localhost:5173
# API will be at http://localhost:3000/dev
```

## Deployment Status: In Progress 🔄

**✅ Core Architecture Implemented:**
- Dual-attestation quest system with atomic operations
- Secure CloudFront infrastructure with private S3
- Centralized state machine authorization logic
- Environment variable management with validation
- Cryptographic signature verification

**🚧 Critical Tasks Remaining:**
- Backend test coverage: 48% → 70% target (integration test fixes needed)
- Frontend test coverage: 7% → 60% target  
- Production-grade XSS protection
- CloudWatch monitoring implementation
- Security audit completion

**📋 Ready for Development/Testing** - Core functionality works but needs testing & security hardening before production deployment.

## Project Structure

- `README.md` - You are here
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) - System design and core principles
- [`DEVELOPMENT.md`](./DEVELOPMENT.md) - Detailed setup and contribution guide
- [`OPERATIONS.md`](./OPERATIONS.md) - Deployment and monitoring
- [API Documentation](https://api.civicforge.org/docs) - Auto-generated from OpenAPI spec

## License

MIT - See [LICENSE](./LICENSE) for details