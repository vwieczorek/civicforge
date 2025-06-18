# CivicForge Security Documentation

*Last Updated: January 17, 2025*

## Security Posture

CivicForge implements defense-in-depth security principles with multiple layers of protection for user data and system integrity. All API endpoints require authentication, data is encrypted at rest and in transit, and the principle of least privilege is enforced throughout the infrastructure.

## Recent Security Remediation (January 17, 2025)

### Critical Vulnerabilities Fixed

1. **Missing API Authentication** ✅ FIXED
   - **Issue**: All API endpoints were publicly accessible without authentication
   - **Fix**: Implemented Cognito JWT authorizer at the `httpApi` level
   - **Implementation**: 
     ```yaml
     httpApi:
       authorizers:
         cognitoJwtAuthorizer:
           type: jwt
           issuerUrl: https://cognito-idp.${region}.amazonaws.com/${userPoolId}
           audience:
             - ${appClientId}
       authorizer: cognitoJwtAuthorizer  # Applied by default
     ```
   - **Exception**: Only `/health` endpoint explicitly set to `authorizer: none`

2. **IAM Wildcard Account ID** ✅ FIXED
   - **Issue**: `createUserTrigger` IAM role used wildcard (`*`) for account ID
   - **Risk**: Could potentially access resources in other AWS accounts
   - **Fix**: Replaced with `${aws:accountId}` for proper account scoping

3. **Missing CORS Configuration** ✅ FIXED
   - **Issue**: No CORS policy defined, preventing frontend integration
   - **Fix**: Added comprehensive CORS configuration with specific allowed origins

## Authentication & Authorization

### AWS Cognito Integration
- **User Pool**: Manages user registration and authentication
- **JWT Tokens**: Stateless authentication for API requests
- **Token Validation**: Automatic validation by API Gateway
- **User Attributes**: userId, email, wallet address (optional)

### API Security
- **Default Protection**: All endpoints require valid JWT token
- **Public Endpoints**: Explicitly marked with `authorizer: none`
- **Rate Limiting**: 100 requests/second, 200 burst capacity
- **Request Validation**: Pydantic models validate all inputs

## Access Control

### IAM Policies (Principle of Least Privilege)

1. **Function-Specific Roles**: Each Lambda has its own IAM role
2. **Granular Permissions**: 
   - Read operations: Limited to specific tables
   - Write operations: Restricted by attributes
   - No blanket admin permissions

3. **DynamoDB Attribute-Level Security**:
   ```yaml
   Condition:
     ForAllValues:StringEquals:
       "dynamodb:Attributes":
         - "xp"
         - "reputation"
         - "updatedAt"
   ```

## Data Protection

### Encryption
- **At Rest**: DynamoDB encryption enabled (AWS-owned keys)
- **In Transit**: HTTPS enforced for all API calls
- **Backups**: Point-in-time recovery enabled for all tables

### Sensitive Data Handling
- **Secrets Management**: AWS Systems Manager Parameter Store
- **No Hardcoded Secrets**: All configuration externalized
- **Environment Variables**: Injected at runtime from SSM

## Dual-Attestation Security

### Cryptographic Signatures (Optional)
- **Algorithm**: Ethereum signatures (EIP-191)
- **Verification**: Server-side signature validation
- **Non-repudiation**: Cryptographic proof of attestation

### Business Logic Protection
- **State Machine**: Enforces valid state transitions
- **Atomic Operations**: Prevents race conditions
- **Role Verification**: Only authorized parties can attest

## Infrastructure Security

### AWS Lambda
- **Isolated Execution**: Each function runs in isolated environment
- **No Persistent State**: Stateless execution model
- **Automatic Patching**: AWS manages runtime security updates

### API Gateway
- **DDoS Protection**: AWS Shield Standard included
- **Request Throttling**: Prevents abuse
- **CloudWatch Integration**: Full request/response logging

### Monitoring & Alerting
- **AWS X-Ray**: Distributed tracing enabled
- **CloudWatch Alarms**: 
  - API error rates
  - DLQ message age
  - Failed user creation attempts
- **Audit Trail**: All API calls logged

## Security Best Practices

### Development
1. **Code Reviews**: All changes require PR approval
2. **Dependency Scanning**: Regular vulnerability checks
3. **Test Coverage**: Security-critical code has 100% coverage
4. **Static Analysis**: Linting enforces secure coding patterns

### Deployment
1. **Environment Separation**: Dev, staging, prod isolation
2. **Least Privilege Deploy**: CI/CD has minimal permissions
3. **Rollback Capability**: Quick reversion if issues detected
4. **Canary Deployments**: Gradual rollout for production

### Operational
1. **Incident Response**: Documented in `/docs/reference/incident-response.md`
2. **Regular Audits**: Quarterly security reviews
3. **Penetration Testing**: Annual third-party assessment
4. **Compliance**: OWASP Top 10 considerations

## Known Security Considerations

### Frontend
- **Error Reporting**: Currently no client-side error monitoring
- **Recommendation**: Implement Sentry or similar service

### Backend
- **Logging Format**: Needs structured JSON format enforcement
- **Recommendation**: Implement AWS Lambda Powertools

## Security Checklist for Developers

Before deploying any changes:

- [ ] No hardcoded secrets or API keys
- [ ] All user inputs validated with Pydantic models
- [ ] New endpoints have authentication (unless explicitly public)
- [ ] IAM permissions follow least privilege
- [ ] Error messages don't leak sensitive information
- [ ] Logging doesn't include PII or secrets
- [ ] Dependencies updated and scanned for vulnerabilities

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT** create a public GitHub issue
2. Email security@civicforge.com with details
3. Include steps to reproduce if possible
4. Allow 48 hours for initial response

## Security Tools & Resources

- **AWS Security Hub**: Centralized security findings
- **AWS GuardDuty**: Threat detection service
- **pip-audit**: Python dependency scanner
- **npm audit**: JavaScript dependency scanner
- **OWASP**: Security best practices reference

## Compliance & Standards

- **OWASP Top 10**: All major vulnerabilities addressed
- **AWS Well-Architected**: Security pillar implemented
- **GDPR**: User data handling compliant
- **SOC2**: Working towards compliance (future)