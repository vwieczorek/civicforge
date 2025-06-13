# Security Model

*Last Updated: December 2024*

## Overview

CivicForge implements defense-in-depth security with multiple layers of protection. This document outlines our security architecture, threat model, and implementation details.

## Table of Contents

1. [Authentication & Authorization](#authentication--authorization)
2. [Data Protection](#data-protection)
3. [API Security](#api-security)
4. [Infrastructure Security](#infrastructure-security)
5. [Cryptographic Features](#cryptographic-features)
6. [Security Best Practices](#security-best-practices)
7. [Incident Response](#incident-response)

## Authentication & Authorization

### AWS Cognito Integration

We use AWS Cognito for user authentication with the following configuration:

```python
# User pool settings
- Password minimum length: 8 characters
- Require uppercase, lowercase, numbers, and symbols
- MFA: Optional (TOTP)
- Account recovery: Email verification
- Token expiration: 1 hour (access), 30 days (refresh)
```

### JWT Token Structure

Access tokens include:
```json
{
  "sub": "user-uuid",
  "cognito:username": "johndoe",
  "email": "john@example.com",
  "email_verified": true,
  "iat": 1640995200,
  "exp": 1640998800
}
```

### Authorization Flow

1. User authenticates with Cognito
2. Cognito returns JWT tokens
3. Frontend includes token in API requests
4. Backend validates token with Cognito
5. Request proceeds if valid

## Data Protection

### At Rest

- **DynamoDB Encryption**: AWS managed encryption (AES-256)
- **S3 Buckets**: Server-side encryption enabled
- **CloudWatch Logs**: Encrypted by default
- **Lambda Environment Variables**: KMS encrypted

### In Transit

- **HTTPS Only**: TLS 1.2+ required
- **Certificate Pinning**: For mobile apps (future)
- **API Gateway**: SSL termination with AWS certificates

### Data Classification

| Data Type | Classification | Protection Level |
|-----------|---------------|------------------|
| Passwords | Critical | Never stored, Cognito managed |
| Email addresses | PII | Encrypted, limited access |
| User IDs | Internal | Pseudonymized UUIDs |
| Quest content | Public | Input sanitization |
| Attestations | Public | Integrity protected |

## API Security

### Input Validation

All inputs are validated using Pydantic models:

```python
class CreateQuestRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=1000)
    rewardXp: int = Field(..., ge=10, le=10000)
    rewardReputation: int = Field(..., ge=1, le=100)
```

### Rate Limiting

Implemented at API Gateway level:
- **Per user**: 1000 requests/hour
- **Per IP**: 100 requests/hour (unauthenticated)
- **Burst**: 2000 requests

### CORS Configuration

```python
ALLOWED_ORIGINS = [
    "https://civicforge.example.com",
    "http://localhost:5173"  # Development only
]
```

### SQL Injection Prevention

- **No SQL**: DynamoDB uses NoSQL queries
- **Parameterized queries**: All database operations use parameters
- **Input sanitization**: HTML/script tags stripped

### XSS Prevention

- **Content-Type validation**: Strict JSON parsing
- **Output encoding**: React handles HTML escaping
- **CSP Headers**: Restrictive Content Security Policy

## Infrastructure Security

### IAM Least Privilege

Each Lambda function has minimal permissions:

```yaml
# Example: Create Quest Lambda
iamRoleStatements:
  - Effect: Allow
    Action:
      - dynamodb:PutItem
    Resource: 
      - arn:aws:dynamodb:${region}:*:table/civicforge-quests
    Condition:
      StringEquals:
        dynamodb:LeadingKeys:
          - ${userId}
```

### Network Isolation

- **VPC**: Lambda functions in private subnets
- **Security Groups**: Restrictive inbound rules
- **NACLs**: Additional network layer protection

### Secrets Management

- **AWS Secrets Manager**: For API keys and sensitive config
- **KMS**: Customer managed keys for encryption
- **Rotation**: Automatic secret rotation enabled

## Cryptographic Features

### EIP-712 Signature Support (Future)

For on-chain attestations:

```solidity
struct Attestation {
    address attester;
    bytes32 questId;
    uint256 rating;
    uint256 timestamp;
    uint256 nonce;
}
```

### Nonce System

Prevents replay attacks:
- Each user has incrementing nonce
- Stored in DynamoDB
- Validated on each signed request

### Hashing

- **Password hashing**: Handled by Cognito (SRP)
- **Data integrity**: SHA-256 for attestation hashes

## Security Best Practices

### Development

1. **Dependency Scanning**
   ```bash
   # Backend
   pip-audit
   
   # Frontend
   npm audit
   ```

2. **Code Review Requirements**
   - Security review for auth changes
   - Automated SAST scanning
   - Manual review for crypto code

3. **Secret Management**
   - Never commit secrets
   - Use environment variables
   - Rotate credentials regularly

### Deployment

1. **Infrastructure as Code**
   - All resources defined in Serverless/CloudFormation
   - Version controlled
   - Peer reviewed

2. **Monitoring**
   - CloudWatch alarms for failed auth
   - Rate limit violations logged
   - Suspicious activity alerts

3. **Backup & Recovery**
   - DynamoDB point-in-time recovery
   - Daily automated backups
   - Tested restore procedures

## Incident Response

### Detection

- CloudWatch Logs analysis
- Failed authentication monitoring
- Rate limit breach alerts
- Error rate thresholds

### Response Plan

1. **Immediate Actions**
   - Isolate affected systems
   - Revoke compromised credentials
   - Enable emergency rate limits

2. **Investigation**
   - Review CloudWatch logs
   - Analyze request patterns
   - Identify attack vectors

3. **Recovery**
   - Patch vulnerabilities
   - Restore from backups if needed
   - Update security rules

4. **Post-Incident**
   - Document lessons learned
   - Update security procedures
   - Implement additional controls

### Contact

Security issues: security@civicforge.example.com

## Compliance

### Standards

- **OWASP Top 10**: Regular assessments
- **AWS Well-Architected**: Security pillar review
- **GDPR**: Privacy by design

### Auditing

- Quarterly security reviews
- Annual penetration testing
- Continuous dependency scanning

## Security Checklist

### Pre-Deployment

- [ ] All dependencies updated
- [ ] Security scan passed
- [ ] IAM permissions reviewed
- [ ] Secrets rotated
- [ ] CORS configured correctly

### Post-Deployment

- [ ] SSL certificates valid
- [ ] Monitoring alerts active
- [ ] Rate limits enforced
- [ ] Logs being collected
- [ ] Backup verified

## Future Enhancements

1. **Web3 Security**
   - Smart contract audits
   - Multi-sig wallet support
   - Hardware wallet integration

2. **Advanced Monitoring**
   - AI-based anomaly detection
   - Real-time threat intelligence
   - Automated response systems

3. **Zero Trust Architecture**
   - Service mesh implementation
   - mTLS between services
   - Policy-based access control