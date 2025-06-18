# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in CivicForge, please report it by emailing security@civicforge.example.com. 

**Please do not report security vulnerabilities through public GitHub issues.**

## Security Best Practices

### Environment Variables

1. **Never commit credentials to version control**
   - Use `.env.example` files with placeholder values
   - Store actual credentials in environment variables or AWS SSM

2. **AWS Credentials**
   - Use IAM roles in production, not access keys
   - Follow principle of least privilege

3. **Frontend Configuration**
   - Cognito IDs in frontend are public by design
   - Never store sensitive secrets in frontend code

### Deployment Security

1. **Pre-deployment Checklist**
   - Run security scans: `bandit -r src/`
   - Check dependencies: `pip-audit`
   - Review IAM policies

2. **Production Configuration**
   - Enable AWS CloudTrail
   - Configure CloudWatch alarms
   - Use encrypted SSM parameters

## Known Security Considerations

### Rate Limiting
Rate limiting is currently implemented at the IP address level to prevent abuse. Per-user rate limiting would require architectural changes to apply rate limiting after authentication.

### Third-Party Dependencies
All dependencies are regularly scanned for vulnerabilities using `pip-audit` and `npm audit`.

## Security Features

- JWT-based authentication via AWS Cognito
- Fine-grained IAM permissions per Lambda function
- Input sanitization to prevent XSS attacks
- DynamoDB encryption at rest
- CloudWatch monitoring and alerting
- Dead Letter Queues for failed operations

## Compliance

This project follows AWS Well-Architected Framework security pillar best practices.