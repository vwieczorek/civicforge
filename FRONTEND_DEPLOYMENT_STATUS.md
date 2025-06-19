# CivicForge Frontend Infrastructure: Current State & Next Steps

**Document Purpose:** This document outlines the current status of the CivicForge frontend infrastructure for the `dev` stage, explains the recent deployment history, and provides a step-by-step guide to finalize the custom domain configuration.

**Date:** June 19, 2025
**Last Updated By:** Claude (Previous Agent)

---

## 1. Executive Summary (TL;DR)

The `dev` stage frontend is successfully deployed and accessible via a CloudFront URL. The initial attempt to attach the custom domain (`dev.civicforge.org`) failed due to a CloudFormation stack rollback. The configuration for the custom domain has been temporarily disabled in `serverless.yml` to allow the core infrastructure to be deployed.

- **Current State:** Application is LIVE at `https://d2wubkvu9vj3ja.cloudfront.net`
- **Next Action:** Re-enable the custom domain configuration in `serverless.yml` and update DNS

---

## 2. Current Infrastructure State

The infrastructure is managed via the CloudFormation stack `civicforge-frontend-infra-dev`, deployed from the `frontend-infra/serverless.yml` file.

### Resources:

- **S3 Bucket (`FrontendBucket`):**
  - **Name:** `civicforge-frontend-dev`
  - **Purpose:** Stores the static frontend assets (React build output)
  - **Access:** The bucket is **private**. Public access is blocked
  - **Versioning:** Enabled

- **CloudFront Distribution (`CloudFrontDistribution`):**
  - **ID:** `E2VPYL2GNIXXBQ`
  - **Domain:** `d2wubkvu9vj3ja.cloudfront.net`
  - **Status:** Deployed and operational
  - **Configuration:**
    - Serves assets from the `civicforge-frontend-dev` S3 bucket
    - Uses **Origin Access Control (OAC)** to securely access S3 content
    - Redirects all HTTP traffic to HTTPS
    - Configured for Single Page Application (SPA) by redirecting 403/404 errors to `/index.html`
    - Cache TTL: Default 1 day, Max 1 year

- **S3 Bucket Policy (`FrontendBucketPolicy`):**
  - Grants `s3:GetObject` permission to the CloudFront distribution
  - Uses condition on `aws:SourceArn` to ensure **only our specific CloudFront distribution** can access the bucket

### Current Access URLs:
- CloudFront: https://d2wubkvu9vj3ja.cloudfront.net ✅ (Working)
- Custom Domain: https://dev.civicforge.org ❌ (Not configured yet)

---

## 3. Deployment History & Incident Debrief

### Timeline of Events:

1. **Initial Deployment Attempt (22:00 UTC)**
   - Goal: Deploy S3, CloudFront, and custom domain configuration
   - Result: Failed due to bucket policy syntax error

2. **Root Cause:**
   - File: `frontend-infra/serverless.yml`
   - Error: IAM condition key was `AWS:SourceArn` (incorrect case)
   - Fix: Should be `aws:SourceArn` (lowercase 'aws')
   - This has been fixed in the file but not deployed

3. **CloudFormation Rollback:**
   - Stack automatically rolled back
   - Deleted CloudFront distribution (ECKDEKF5QM695)
   - Could not delete S3 bucket (contained files)
   - Left stack in `UPDATE_ROLLBACK_COMPLETE` state

4. **Recovery Actions Taken:**
   - Emptied and deleted S3 bucket manually
   - Removed entire CloudFormation stack
   - Commented out custom domain configuration (lines 92-97)
   - Redeployed successfully without custom domain

### Current Git Status:
```
- All changes committed
- Last commit: c73e11c (fix: Complete CloudFront deployment fixes)
- Branch: main
```

---

## 4. Action Plan: Enabling the Custom Domain

### Prerequisites Checklist:
- [x] ACM Certificate exists: `arn:aws:acm:us-east-1:211125472754:certificate/b13d3702-b386-4343-936c-5e803c2bea77`
- [x] Certificate status: ISSUED
- [x] Certificate region: us-east-1 (required for CloudFront)
- [x] DNS access: Route53 hosted zone exists for civicforge.org

### Step 1: Update `serverless.yml`

Uncomment the custom domain configuration:

```yaml
# File: frontend-infra/serverless.yml
# Lines to uncomment: 92-97

          Aliases:
            - ${self:custom.domainName.${self:provider.stage}, ''}
          ViewerCertificate:
            AcmCertificateArn: ${self:custom.certificateArn.${self:provider.stage}, ''}
            SslSupportMethod: sni-only
            MinimumProtocolVersion: TLSv1.2_2021
```

### Step 2: Deploy the Infrastructure Update

```bash
cd frontend-infra
serverless deploy --stage dev --region us-east-1
```

Expected duration: 10-20 minutes (CloudFront global propagation)

### Step 3: Update DNS

**Option A: Using AWS Route 53 (Recommended)**
```bash
# The DNS record currently points to old distribution d13jkegav561oz.cloudfront.net
# Update to point to new distribution:

aws route53 change-resource-record-sets \
  --hosted-zone-id Z050840624HB56C0NJOA1 \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "dev.civicforge.org.",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "d2wubkvu9vj3ja.cloudfront.net"}]
      }
    }]
  }'
```

### Step 4: Verify Deployment

1. Check CloudFormation stack status:
   ```bash
   aws cloudformation describe-stacks --stack-name civicforge-frontend-infra-dev --query 'Stacks[0].StackStatus'
   ```

2. Test HTTPS access:
   ```bash
   curl -I https://dev.civicforge.org
   ```

3. Verify in browser and check SSL certificate

---

## 5. Troubleshooting Guide

### Common Issues:

1. **CNAMEAlreadyExists Error**
   - Cause: DNS already points to another CloudFront distribution
   - Fix: Update DNS first, then add alias to CloudFront

2. **403 Forbidden from CloudFront**
   - Cause: Missing or incorrect S3 bucket policy
   - Fix: Check bucket policy has correct distribution ARN

3. **Stack Rollback**
   - Check CloudFormation events for specific error
   - Common: Bucket not empty, invalid policy syntax

### Useful Commands:

```bash
# Check CloudFront distribution
aws cloudfront get-distribution --id E2VPYL2GNIXXBQ

# Check S3 bucket policy
aws s3api get-bucket-policy --bucket civicforge-frontend-dev

# Check DNS resolution
dig dev.civicforge.org @8.8.8.8

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id E2VPYL2GNIXXBQ --paths "/*"
```

---

## 6. Architecture Diagram

```
┌─────────────────┐     HTTPS      ┌──────────────────┐
│   dev.civicforge│ ───────────────▶│   CloudFront     │
│      .org       │     (CNAME)     │  E2VPYL2GNIXXBQ  │
└─────────────────┘                 └────────┬─────────┘
                                             │
                                             │ OAC
                                             ▼
                                    ┌──────────────────┐
                                    │    S3 Bucket     │
                                    │ civicforge-      │
                                    │ frontend-dev     │
                                    └──────────────────┘
```

---

## 7. Important Notes

- The S3 bucket is PRIVATE and should remain so
- CloudFront uses Origin Access Control (OAC), not the older OAI
- The bucket policy must use lowercase `aws:SourceArn`
- Frontend build artifacts are already deployed and working
- No changes needed to application code

---

## Next Agent Action Required

Please complete the custom domain setup by following the action plan in Section 4. The infrastructure is healthy and just needs the final configuration step.