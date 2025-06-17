# CivicForge Documentation Hub

Welcome to the central documentation for CivicForge. All project documentation is organized here for easy navigation.

---

## 🚀 Quick Links

- **[Live Project Status](../PROJECT_STATUS.md)** - Current test metrics, blockers, and progress (Single Source of Truth)
- **[MVP Deployment Plan](../MVP_DEPLOYMENT_PLAN.md)** - Roadmap to production launch
- **[Testing Guide](./TESTING.md)** - Comprehensive testing documentation with recent fixes

---

## 📚 Getting Started

### For New Contributors
1. Start with the [Project README](../README.md) for a high-level overview
2. Follow the [Contributing Guide](../CONTRIBUTING.md) for development setup
3. Review the [Architecture Overview](./reference/architecture.md) to understand the system

### For Developers
1. Check [Current Project Status](../PROJECT_STATUS.md) for latest updates
2. Review [Testing Guide](./TESTING.md) for test patterns and debugging
3. See [API Reference](./reference/api-reference.md) for endpoint documentation

---

## 📖 Documentation Structure

This documentation follows the [Diátaxis framework](https://diataxis.fr/) for technical documentation.

### 🎓 Tutorials (Learning-Oriented)
Step-by-step guides for getting started

- [Local Development Setup](./tutorials/local-development-setup.md)
- [Creating Your First Quest](./tutorials/creating-first-quest.md) *(Coming Soon)*
- [Running Tests Locally](./TESTING.md#running-tests)

### 🛠️ How-To Guides (Task-Oriented)
Practical guides for specific tasks

- [Deployment Runbook](./DEPLOYMENT_RUNBOOK.md) - Step-by-step deployment guide
- [Add a New API Endpoint](../CONTRIBUTING.md#add-a-new-api-endpoint)
- [Debug Failed Tests](./TESTING.md#debugging-failed-tests)
- [Deploy to AWS](./how-to-guides/deploying-to-aws.md)
- [Configure SSM Parameters](../MVP_DEPLOYMENT_PLAN.md#phase-2-infrastructure-setup)

### 📋 Reference (Information-Oriented)
Technical descriptions and specifications

- [API Reference](./reference/api-reference.md) - REST API endpoints
- [Backend Architecture](./reference/backend-architecture.md) - Lambda-per-operation design
- [Frontend Architecture](./reference/frontend-architecture.md) - React application structure
- [Security Features](./reference/security-features.md) - Security implementation
- [Data Models](./reference/data-models.md) - Database schema and entities
- [Incident Response](./reference/incident-response.md) - Production incident procedures
- [Component Library](./components/) - Frontend component docs
  - [QuestFilters](./components/QuestFilters.md)
  - [WorkSubmissionModal](./components/WorkSubmissionModal.md)

### 💡 Explanation (Understanding-Oriented)
Conceptual guides and background

- [Dual-Attestation System](./explanation/dual-attestation-concept.md)
- [Quest State Machine](./explanation/quest-state-machine.md) - Core business logic
- [Reputation Mechanics](./explanation/reputation-system.md) *(Coming Soon)*
- [Testing Philosophy](./TESTING.md#overview)
- [Serverless Design Choices](./explanation/serverless-design-choices.md)

---

## 📊 Project Management

### Status and Planning
- **[PROJECT_STATUS.md](../PROJECT_STATUS.md)** - Live metrics and blockers
- **[MVP_DEPLOYMENT_PLAN.md](../MVP_DEPLOYMENT_PLAN.md)** - Deployment roadmap
- **[CHANGELOG.md](../CHANGELOG.md)** - Version history

### Development Process
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Contribution guidelines
- **[CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)** - Community standards
- **[SECURITY.md](../SECURITY.md)** - Security policies

---

## 🚧 Documentation Status

### Recently Updated (January 2025)
- ✅ [TESTING.md](./TESTING.md) - Consolidated all testing documentation, now the single source of truth
- ✅ [PROJECT_STATUS.md](../PROJECT_STATUS.md) - Updated with latest metrics (88% backend coverage, E2E tests fixed)
- ✅ [README.md](../README.md) - Updated with current test metrics and deployment status
- ✅ [DEPLOYMENT_RUNBOOK.md](./DEPLOYMENT_RUNBOOK.md) - Comprehensive deployment procedures
- ✅ [backend-architecture.md](./reference/backend-architecture.md) - Lambda-per-operation architecture documented
- ✅ [security-features.md](./reference/security-features.md) - NEW: Security implementation details
- 📌 [testing-strategy.md](./reference/testing-strategy.md) - DEPRECATED: See TESTING.md instead
- 📌 [deploying-to-aws.md](./how-to-guides/deploying-to-aws.md) - DEPRECATED: See DEPLOYMENT_RUNBOOK.md instead

### Recently Created (January 2025)
- ✅ [Frontend Architecture Guide](./reference/frontend-architecture.md) - Complete frontend architecture documentation
- ✅ [Incident Response Guide](./reference/incident-response.md) - Production incident procedures
- ✅ [Quest State Machine](./explanation/quest-state-machine.md) - Core business logic explained
- ✅ [CHANGELOG.md](../CHANGELOG.md) - Version history and changes

### Needs Creation
- [ ] Performance Tuning Guide
- [ ] Monitoring and Observability Guide
- [ ] API Rate Limiting Guide

### Needs Update
- [ ] Component documentation for new features
- [ ] Architecture diagrams with current state
- [ ] Security audit results

---

## 🔍 Finding Information

### By Topic
- **Testing Issues?** → [TESTING.md](./TESTING.md)
- **Deployment Blocked?** → [PROJECT_STATUS.md](../PROJECT_STATUS.md)
- **API Questions?** → [API Reference](./reference/api-reference.md)
- **Setup Problems?** → [CONTRIBUTING.md](../CONTRIBUTING.md)

### By Role
- **Frontend Developer** → Start with [Component Docs](./components/)
- **Backend Developer** → See [API Reference](./reference/api-reference.md)
- **DevOps/SRE** → Check [Deployment Plan](../MVP_DEPLOYMENT_PLAN.md)
- **Product Manager** → Review [Project Status](../PROJECT_STATUS.md)

---

## 📝 Contributing to Documentation

We follow these principles for documentation:

1. **Single Source of Truth**: No duplicate information
2. **Living Documentation**: Keep it current with code
3. **User-Focused**: Write for your audience
4. **Searchable**: Use clear headings and keywords
5. **Testable**: Include examples that can be verified

To contribute:
1. Check if documentation already exists
2. Follow the Diátaxis framework category
3. Update this INDEX.md if adding new files
4. Link from relevant existing docs
5. Test all code examples

---

## 🆘 Getting Help

- **Questions?** → Check [FAQ](./faq.md) *(Coming Soon)*
- **Found an Issue?** → [Report on GitHub](https://github.com/civicforge/civicforge/issues)
- **Need Support?** → Contact the development team

---

*Last Updated: January 2025*