# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive signature verification tests for security
- Lambda-per-operation architecture for enhanced security isolation
- GSI fallback logic for DynamoDB operations
- Dispute endpoint with atomic operations
- Global exception handler with request tracking
- Frontend WorkSubmissionModal component
- Frontend QuestFilters component with advanced search
- Comprehensive deployment runbook
- Backend architecture documentation
- Security features documentation

### Changed
- Backend test coverage increased from 85% to 88%
- E2E tests fixed to work with custom JWT authentication
- Documentation consolidated into single entry point (docs/INDEX.md)
- Deployment scripts enhanced with safety checks and rollback procedures
- DynamoDB client refactored for better connection management

### Fixed
- E2E test configuration mismatch with custom auth
- FastAPI TestClient exception handling in tests
- Duplicate CloudWatch alarm definitions
- GSI fallback for missing indexes
- Concurrent attestation race conditions

### Security
- Added comprehensive test coverage for signature verification
- Implemented least-privilege IAM policies per Lambda function
- Enhanced input validation and sanitization
- Added rate limiting to API Gateway

## [0.3.0] - 2024-12-16

### Added
- Dependency injection implementation for better testability
- Atomic database operations to prevent race conditions
- Comprehensive backend testing suite (269 tests)
- Frontend unit test coverage
- Staging environment configuration

### Changed
- Migrated from legacy architecture to serverless
- Simplified authentication flow using AWS Cognito
- Updated all dependencies to latest stable versions

### Fixed
- Authentication flow inconsistencies
- Database connection pooling issues
- Frontend routing problems

## [0.2.0] - 2024-11-15

### Added
- Quest dispute functionality
- User profile management
- Wallet address integration
- Failed reward retry mechanism

### Changed
- Enhanced state machine for quest lifecycle
- Improved error handling across all endpoints

## [0.1.0] - 2024-10-01

### Added
- Initial dual-attestation quest system
- Basic user authentication with Cognito
- Quest creation, claiming, and submission
- XP and reputation reward system
- Frontend React application
- Backend FastAPI application
- DynamoDB database integration

[Unreleased]: https://github.com/civicforge/civicforge/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/civicforge/civicforge/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/civicforge/civicforge/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/civicforge/civicforge/releases/tag/v0.1.0