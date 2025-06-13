# CivicForge Documentation

Welcome to the CivicForge documentation! This documentation is organized using the [Diátaxis](https://diataxis.fr/) framework, which structures content based on user needs.

## 📚 Documentation Structure

### [Tutorials](./tutorials/) - Learning-oriented
*Start here if you're new to CivicForge*

- [Local Development Setup](./tutorials/local-development-setup.md) - Get your development environment running
- [First Quest Walkthrough](./tutorials/first-quest-walkthrough.md) - Create, claim, and complete your first quest

### [How-To Guides](./how-to-guides/) - Task-oriented
*Practical guides for specific tasks*

- [Deploying to AWS](./how-to-guides/deploying-to-aws.md) - Deploy CivicForge to production
- [Running Backend Tests](./how-to-guides/running-backend-tests.md) - Execute the backend test suite
- [Running Frontend Tests](./how-to-guides/running-frontend-tests.md) - Execute the frontend test suite
- [Add New API Endpoint](./how-to-guides/add-new-api-endpoint.md) - Extend the API
- [Update Database Schema](./how-to-guides/update-database-schema.md) - Modify DynamoDB tables
- [Debug Lambda Locally](./how-to-guides/debug-lambda-locally.md) - Troubleshoot Lambda functions
- [Manage Feature Flags](./how-to-guides/manage-feature-flags.md) - Control feature rollout
- [Troubleshoot Common Issues](./how-to-guides/troubleshoot-common-issues.md) - Fix common problems

### [Reference](./reference/) - Information-oriented
*Technical specifications and details*

- [Architecture Overview](./reference/architecture.md) - System design and components
- [API Reference](./reference/api-reference.md) - Complete API documentation
- [Data Models](./reference/data-models.md) - Database schemas and relationships
- [Security Model](./reference/security-model.md) - Authentication, authorization, and security measures
- [Testing Strategy](./reference/testing-strategy.md) - Testing philosophy and current status
- [Operations Guide](./reference/operations.md) - Production operations and monitoring

### [Explanation](./explanation/) - Understanding-oriented
*Background, concepts, and decisions*

- [Project Goals](./explanation/project-goals.md) - Vision and objectives
- [Dual Attestation Concept](./explanation/dual-attestation-concept.md) - How trust is built
- [Serverless Design Choices](./explanation/serverless-design-choices.md) - Why we chose AWS Lambda

### [Architecture Decision Records](./adr/)
*Historical record of architectural decisions*

## 🚀 Quick Links

### For New Contributors
1. Start with [Local Development Setup](./tutorials/local-development-setup.md)
2. Read the [Contributing Guide](../CONTRIBUTING.md)
3. Review the [Architecture Overview](./reference/architecture.md)

### For Developers
- [API Reference](./reference/api-reference.md) - Endpoint documentation
- [Testing Strategy](./reference/testing-strategy.md) - How we test
- [Security Model](./reference/security-model.md) - Security considerations

### For Operations
- [Deploying to AWS](./how-to-guides/deploying-to-aws.md) - Deployment guide
- [Operations Guide](./reference/operations.md) - Monitoring and maintenance
- [Troubleshoot Common Issues](./how-to-guides/troubleshoot-common-issues.md) - Problem resolution

## 📝 Documentation Standards

### Writing Style
- Use clear, concise language
- Include code examples where helpful
- Add diagrams for complex concepts
- Keep documents focused on their category (tutorial, how-to, reference, or explanation)

### Maintenance
- Each document includes a "Last Updated" date
- Review documentation quarterly
- Update immediately when APIs or processes change
- Archive truly obsolete content to `_archive/`

## 🔍 Finding Information

### By Role
- **Frontend Developer**: Start with [Frontend Tests](./how-to-guides/running-frontend-tests.md) and [Architecture](./reference/architecture.md#frontend-architecture)
- **Backend Developer**: See [Backend Tests](./how-to-guides/running-backend-tests.md) and [API Reference](./reference/api-reference.md)
- **DevOps Engineer**: Review [Operations](./reference/operations.md) and [Deploying to AWS](./how-to-guides/deploying-to-aws.md)
- **Security Auditor**: Read [Security Model](./reference/security-model.md) and [Architecture](./reference/architecture.md#security-architecture)

### By Topic
- **Testing**: [Testing Strategy](./reference/testing-strategy.md), [Backend Tests](./how-to-guides/running-backend-tests.md), [Frontend Tests](./how-to-guides/running-frontend-tests.md)
- **Deployment**: [Deploying to AWS](./how-to-guides/deploying-to-aws.md), [Operations](./reference/operations.md)
- **Development**: [Local Setup](./tutorials/local-development-setup.md), [Contributing](../CONTRIBUTING.md)
- **Architecture**: [Overview](./reference/architecture.md), [Data Models](./reference/data-models.md), [ADRs](./adr/)

## 📚 External Resources

- [Diátaxis Framework](https://diataxis.fr/) - Documentation methodology
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [React Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)

---

*Last Updated: December 2024*