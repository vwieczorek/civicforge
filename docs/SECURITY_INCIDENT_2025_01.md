# Security Incident Report: Cognito Credentials in Version Control

## Incident Summary
- **Date Discovered**: January 2025
- **Severity**: Medium
- **Type**: Configuration Data Exposure
- **Status**: Remediated

## Description
AWS Cognito User Pool ID and App Client ID were found in frontend environment files that were tracked by git. While these IDs are semi-public (sent to browsers), they should be managed through deployment configuration rather than version control.

### Exposed Data
- User Pool ID: `us-east-1_wKpnasV5v`
- App Client ID: `71uqkredjv9aj4icaa2crlvvp3`
- Files: `frontend/.env`, `frontend/.env.development`

## Impact Assessment
- **Low Risk**: These are public client IDs, not secret keys
- **Medium Concern**: Poor security practice that could lead to:
  - Unauthorized app registrations
  - Potential phishing attacks using legitimate pool IDs
  - Difficulty rotating credentials

## Remediation Steps Taken

### Immediate Actions (Completed)
1. ✅ Removed `.env` files from filesystem
2. ✅ Updated `.gitignore` to prevent future commits
3. ✅ Created `.env.example` with placeholder values
4. ✅ Documented incident in `SANITIZATION_SUMMARY.md`

### Rotation Scripts Created
1. ✅ `scripts/rotate_cognito_credentials.sh` - Automates credential rotation
2. ✅ `scripts/clean_git_history.sh` - Guide for cleaning git history

### Pending Actions
1. ⏳ Execute credential rotation script
2. ⏳ Clean git history if needed
3. ⏳ Redeploy all services with new credentials

## Lessons Learned

### What Went Wrong
- Environment files with real values were committed to version control
- No pre-commit hooks to prevent sensitive file commits
- Missing documentation about proper credential management

### Improvements Implemented
1. **Enhanced .gitignore**: Now explicitly excludes all .env variants
2. **Documentation**: Created comprehensive deployment guides
3. **Automation**: Rotation scripts for quick response
4. **Security Policy**: Added SECURITY.md with best practices

## Prevention Measures

### Technical Controls
```bash
# Pre-commit hook to prevent .env commits
#!/bin/bash
if git diff --cached --name-only | grep -E "\.env$|\.env\.|aws_access|aws_secret|api_key|private_key"; then
  echo "ERROR: Attempting to commit sensitive files"
  echo "Remove them with: git reset HEAD <file>"
  exit 1
fi
```

### Process Improvements
1. Use SSM Parameter Store for all configuration
2. Never commit real credentials, even "public" ones
3. Regular security audits of version control
4. Automated scanning for exposed credentials

## References
- [AWS Cognito Security Best Practices](https://docs.aws.amazon.com/cognito/latest/developerguide/security-best-practices.html)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
- Internal: `SECURITY.md`, `SANITIZATION_SUMMARY.md`

---
Report prepared by: Security Review Process
Date: January 2025