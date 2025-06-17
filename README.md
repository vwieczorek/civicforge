# CivicForge

> A decentralized platform for community-driven civic engagement through dual-attestation quest completion

[![Backend Tests](https://img.shields.io/badge/backend%20tests-261%20passing-brightgreen)]()
[![Backend Coverage](https://img.shields.io/badge/backend%20coverage-88%25-brightgreen)]()
[![Frontend Tests](https://img.shields.io/badge/frontend%20tests-96%20passing-brightgreen)]()
[![Frontend Coverage](https://img.shields.io/badge/frontend%20coverage-71%25-brightgreen)]()
[![Deployment](https://img.shields.io/badge/deployment-ready-brightgreen)]()

📊 **[View Detailed Project Status](./PROJECT_STATUS.md)**

## Overview

CivicForge enables communities to create, complete, and verify civic improvement tasks through a dual-attestation system. Quest creators define tasks with rewards, community members complete them, and creators verify completion - building trust through peer verification rather than centralized authority.

## Key Features

- 🎯 **Dual-Attestation System**: Both quest creator and performer must attest to completion
- 💰 **Flexible Rewards**: Experience points (XP) and reputation for verified contributions
- ⚡ **Serverless Architecture**: Built on AWS Lambda + DynamoDB for infinite scalability
- 🔒 **Secure Authentication**: AWS Cognito integration with JWT tokens
- 🧪 **Comprehensive Testing**: 88% backend coverage, 71% frontend coverage
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
git clone https://github.com/civicforge/civicforge.git
cd civicforge

# Backend Setup & Start (Terminal 1)
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
npm run local

# Frontend Setup & Start (Terminal 2)
# Open a new terminal window for the frontend.
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

For comprehensive documentation, please refer to the following:

### 🚀 Quick Links
- **[Handover Document](./HANDOVER.md)** - Recent security fixes and next steps
- **[Project Status](./PROJECT_STATUS.md)** - Current progress, priorities, and deployment readiness
- **[Architecture Overview](./docs/ARCHITECTURE.md)** - System design and component interaction
- **[Security Guide](./docs/SECURITY.md)** - Security measures and best practices
- **[Testing Strategy](./docs/TESTING.md)** - Test coverage and instructions
- **[Deployment Runbook](./docs/DEPLOYMENT_RUNBOOK.md)** - Step-by-step deployment guide

### 📚 Detailed Documentation
- [Getting Started Tutorial](./docs/tutorials/local-development-setup.md)
- [API Reference](./docs/reference/api-reference.md)
- [Contributing Guide](./CONTRIBUTING.md)
- [Backend Architecture](./docs/reference/backend-architecture.md)
- [Frontend Architecture](./docs/reference/frontend-architecture.md)

### Component Documentation
- 🎯 [QuestFilters](./docs/components/QuestFilters.md) - Advanced quest search and filtering
- 📝 [WorkSubmissionModal](./docs/components/WorkSubmissionModal.md) - Work submission interface

### Project Management
- 📊 [Current Status](./PROJECT_STATUS.md) - Real-time project status and metrics
- 🚦 [MVP Deployment Plan](./MVP_DEPLOYMENT_PLAN.md) - Path to production

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
- **Authentication**: Custom JWT-based
- **Testing**: Vitest + React Testing Library + Playwright

### Infrastructure
- **Compute**: AWS Lambda (serverless functions)
- **API Gateway**: AWS API Gateway with request validation
- **Storage**: DynamoDB with on-demand scaling
- **Auth**: AWS Cognito user pools
- **Monitoring**: CloudWatch logs and metrics

## Current Status

### ✅ Production-Ready
- Backend API with 88% test coverage (261 tests passing)
- Frontend with 71% test coverage (96 tests passing)
- E2E tests configured and working with custom JWT flow
- Comprehensive error handling and retry logic
- Security hardening with least-privilege IAM
- Staging environment fully configured with Cognito
- Signature verification with comprehensive test coverage
- Lambda-per-operation architecture for security isolation
- Complete deployment automation with rollback procedures

### 🚧 In Progress
- Documentation consolidation and updates
- Frontend architecture guide
- Incident response procedures

### 🔜 Coming Soon
- Advanced reputation algorithms
- Mobile application
- Real-time updates via WebSockets
- Blockchain integration for attestations
- Community governance features

## Deployment

### Prerequisites
- AWS Account with appropriate IAM permissions
- AWS CLI configured
- Node.js 18+ and Python 3.11+
- Environment-specific SSM parameters configured

### Deployment Commands
```bash
# Check MVP readiness
npm run check:mvp

# Deploy to development
npm run deploy:dev

# Deploy to staging
npm run deploy:staging

# Deploy to production (requires all tests passing)
npm run deploy:prod
```

### Deployment Readiness
✅ **Project is deployment-ready!**
- Frontend: All 96 tests passing (71% coverage)
- Backend: All 261 tests passing (88% coverage)
- E2E tests: Fully configured and passing
- Staging environment: Fully configured with Cognito
- Security: Signature verification implemented and tested
- Infrastructure: Lambda-per-operation architecture deployed
- See [Project Status](./PROJECT_STATUS.md) for details

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