# CivicForge

> A decentralized platform for community-driven civic engagement through dual-attestation quest completion

[![Backend Coverage](https://img.shields.io/badge/backend%20coverage-85%25-brightgreen.svg)]()
[![Frontend Coverage](https://img.shields.io/badge/frontend%20coverage-67%25-yellow.svg)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()

## Overview

CivicForge enables communities to create, complete, and verify civic improvement tasks through a dual-attestation system. Quest creators define tasks with rewards, community members complete them, and creators verify completion - building trust through peer verification rather than centralized authority.

## Key Features

- 🎯 **Dual-Attestation System**: Both quest creator and performer must attest to completion
- 💰 **Flexible Rewards**: Experience points (XP) and reputation for verified contributions
- ⚡ **Serverless Architecture**: Built on AWS Lambda + DynamoDB for infinite scalability
- 🔒 **Secure Authentication**: AWS Cognito integration with JWT tokens
- 🧪 **Comprehensive Testing**: 85%+ backend coverage, growing frontend coverage
- 🚀 **Modern Frontend**: React + TypeScript with real-time updates

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- AWS CLI configured with appropriate credentials
- Docker (for local DynamoDB testing)

### Local Development

```bash
# Clone the repository
git clone https://github.com/your-org/civicforge.git
cd civicforge

# Install dependencies
npm install

# Start backend services
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
npm run local

# In another terminal, start the frontend
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173 to see the application.

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# E2E tests
cd frontend
npm run test:e2e
```

## Project Structure

```
civicforge/
├── backend/               # Python/FastAPI Lambda functions
│   ├── src/              # Core application code
│   ├── handlers/         # Lambda function handlers
│   ├── tests/            # Backend test suite
│   └── serverless.yml    # AWS Lambda configuration
├── frontend/             # React/TypeScript application
│   ├── src/              # Frontend source code
│   ├── e2e/              # Playwright E2E tests
│   └── vite.config.ts    # Build configuration
├── docs/                 # Comprehensive documentation
│   ├── tutorials/        # Getting started guides
│   ├── how-to-guides/    # Task-specific guides
│   ├── reference/        # Technical reference
│   └── explanation/      # Concepts and background
└── scripts/              # Deployment and utility scripts
```

## Documentation

For comprehensive documentation, see the [docs directory](./docs/):

- 📚 [Getting Started Tutorial](./docs/tutorials/local-development-setup.md)
- 🏗️ [Architecture Overview](./docs/reference/architecture.md)
- 📡 [API Reference](./docs/reference/api-reference.md)
- 🤝 [Contributing Guide](./CONTRIBUTING.md)
- 🔐 [Security Model](./docs/reference/security-model.md)
- 🧪 [Testing Strategy](./docs/reference/testing-strategy.md)

## Core Workflow

1. **Create Quest**: Authenticated users create quests with descriptions and rewards
2. **Claim Quest**: Community members browse and claim available quests
3. **Submit Work**: Performers submit evidence of completed work
4. **Dual Attestation**: Creator reviews and attests to completion
5. **Reward Distribution**: XP and reputation automatically distributed upon attestation

## Technology Stack

### Backend
- **Runtime**: Python 3.11 on AWS Lambda
- **API**: FastAPI with automatic OpenAPI documentation
- **Database**: DynamoDB with single-table design
- **Authentication**: AWS Cognito with JWT tokens
- **Testing**: Pytest with 85%+ coverage

### Frontend
- **Framework**: React 18 with TypeScript
- **Routing**: React Router v6
- **State Management**: React hooks + Context API
- **Authentication**: AWS Amplify
- **Testing**: Vitest + React Testing Library + Playwright

### Infrastructure
- **Compute**: AWS Lambda (serverless functions)
- **API Gateway**: AWS API Gateway with request validation
- **Storage**: DynamoDB with on-demand scaling
- **Auth**: AWS Cognito user pools
- **Monitoring**: CloudWatch logs and metrics

## Current Status

### ✅ Production-Ready
- Backend API with 85% test coverage
- Comprehensive error handling and retry logic
- Security hardening with least-privilege IAM
- Full documentation suite

### 🚧 In Progress
- Frontend test coverage improvement (currently 67%, target 80%)
- E2E test suite expansion
- Performance optimizations

### 🔜 Coming Soon
- EIP-712 cryptographic signatures for on-chain attestations
- Advanced reputation algorithms
- Mobile application

## Contributing

We welcome contributions! Please see our [Contributing Guide](./CONTRIBUTING.md) for details on:
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

## Security

Security is paramount in CivicForge. Key measures include:
- JWT-based authentication with refresh tokens
- IAM least-privilege principles
- Input validation and sanitization
- Rate limiting and DDoS protection
- Comprehensive security auditing

See our [Security Model](./docs/reference/security-model.md) for details.

## Support

- 📖 [Documentation](./docs/)
- 🐛 [GitHub Issues](https://github.com/your-org/civicforge/issues)
- 💬 [GitHub Discussions](https://github.com/your-org/civicforge/discussions)

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

---

Built with ❤️ for civic engagement