# CLAUDE.md - CivicForge Development Guide

This document contains important information for AI agents working on the CivicForge project.

## Project Overview

CivicForge is a peer-to-peer trust platform with:
- Frontend: React + TypeScript + Vite
- Backend: Python FastAPI + AWS Lambda (Serverless)
- Infrastructure: AWS (S3, CloudFront, DynamoDB, Cognito)

## Key Commands

### Frontend
```bash
cd frontend
npm install
npm run dev          # Development server
npm run build        # Production build
npm run test         # Run tests
npm run lint         # Run linter
npm run type-check   # TypeScript type checking
```

### Backend
```bash
cd backend
pip install -r requirements.txt
pytest               # Run tests
black src/           # Format code
mypy src/ --ignore-missing-imports  # Type checking
```

### Infrastructure
```bash
cd frontend-infra
npx serverless deploy --stage dev    # Deploy frontend infrastructure
cd ../backend
npx serverless deploy --stage dev    # Deploy backend
```

## Environment Configuration

Frontend environment variables are fetched from AWS SSM during build:
- VITE_USER_POOL_ID
- VITE_USER_POOL_CLIENT_ID
- VITE_API_URL
- VITE_AWS_REGION

## Testing

- Frontend tests use Vitest
- Backend tests use pytest
- Coverage requirements: 70% for backend

---

# Frontend Infrastructure Deployment Learnings

This section captures critical insights and common pitfalls encountered during the deployment and management of the CivicForge frontend infrastructure.

## Key Learnings

### 1. CloudFormation IAM Condition Keys are Case-Sensitive

**Learning:** CloudFormation bucket policies, specifically IAM condition keys like `aws:SourceArn`, are case-sensitive. Using `AWS:SourceArn` (uppercase 'A') will cause a deployment failure and rollback.

**Detail:** The correct casing for the `SourceArn` condition within an S3 bucket policy is `aws:SourceArn`. This was the root cause of an initial CloudFormation stack rollback.

**Reference:**
```yaml
Condition:
  StringEquals:
    'aws:SourceArn': !Sub 'arn:aws:cloudfront::${AWS::AccountId}:distribution/${CloudFrontDistribution}'
```

### 2. CloudFormation Rollbacks and Non-Empty S3 Buckets

**Learning:** During a CloudFormation stack rollback, S3 buckets that contain objects cannot be automatically deleted by CloudFormation.

**Action:** If a `ROLLBACK_FAILED` state occurs:
1. Navigate to S3 console
2. Empty the bucket of all contents (including versions if versioning is enabled)
3. Delete the bucket manually
4. Then delete the CloudFormation stack

### 3. CloudFront Distribution Propagation Times

**Learning:** CloudFront distribution deployments take 10-20 minutes to propagate globally.

**Action:** After a `serverless deploy` that modifies CloudFront, allow sufficient time for changes to propagate before verifying.

### 4. Custom Domain Setup Order

**Learning:** When configuring custom domains for CloudFront, the CloudFront distribution must be updated with the domain alias and SSL certificate BEFORE updating DNS records.

**Action:** Follow this sequence:
1. Update CloudFront with alias and certificate
2. Wait for CloudFront propagation
3. Update DNS to point to CloudFront

### 5. Frontend Build Optimization

**Learning:** The frontend build process uses `tsconfig.build.json` to exclude test files from production builds.

**Detail:** This reduces bundle size and ensures test code doesn't reach production. The build command uses:
```bash
npm run build  # Uses: tsc -p tsconfig.build.json && vite build
```

## Common Issues and Solutions

### TypeScript Build Errors
- Check if imports are used (remove unused imports)
- Verify test files are excluded in tsconfig.build.json
- Use `noUnusedLocals: false` for build config if needed

### CloudFront 403 Errors
- Verify S3 bucket policy exists and has correct syntax
- Check Origin Access Control (OAC) configuration
- Ensure bucket policy references correct CloudFront distribution ARN

### DNS Configuration
- For Route53: Use A record with Alias to CloudFront
- For other providers: Use CNAME record
- Allow time for DNS propagation (5-10 minutes typically)