# CloudFront 403 Error Fix

## Problem Summary
The CloudFront 403 error at dev.civicforge.org was caused by conflicting S3 bucket configurations:
- The Serverless Framework (`frontend-infra/serverless.yml`) correctly configured a private S3 bucket with CloudFront Origin Access Control (OAC)
- The GitHub Actions deployment workflow was trying to make the S3 bucket public, which conflicted with the security settings

## Solution Applied

### 1. Fixed Deployment Workflow
Updated `.github/workflows/deploy.yml` to:
- Remove S3 bucket creation (managed by Serverless Framework)
- Remove S3 static website hosting configuration
- Remove public bucket policy attempts
- Add CloudFront cache invalidation after deployment

### 2. Infrastructure Setup
The frontend infrastructure uses:
- **Private S3 bucket** with public access blocked
- **CloudFront distribution** with Origin Access Control (OAC) for secure access
- **Automatic SPA routing** with custom error responses

## Deployment Instructions

### First-Time Setup (or Infrastructure Changes)
1. Deploy the frontend infrastructure:
   ```bash
   cd frontend-infra
   ./deploy.sh dev  # or staging/prod
   ```

2. Verify the infrastructure is created:
   ```bash
   aws cloudformation describe-stacks --stack-name civicforge-frontend-infra-dev
   ```

### Regular Deployments
The GitHub Actions workflow will now:
1. Build the frontend application
2. Sync files to the S3 bucket
3. Invalidate CloudFront cache
4. Display the CloudFront URL (not S3 URL)

### Important URLs
- **Development**: Access via CloudFront URL from stack outputs (not S3 directly)
- **Custom Domain**: If using dev.civicforge.org, ensure DNS points to CloudFront distribution

### Testing the Fix
1. Check CloudFront distribution status:
   ```bash
   aws cloudfront get-distribution --id YOUR_DISTRIBUTION_ID
   ```

2. Verify S3 bucket is private:
   ```bash
   aws s3api get-bucket-policy --bucket civicforge-frontend-dev
   # Should show policy allowing only CloudFront access
   ```

3. Test access:
   - CloudFront URL should work ✅
   - Direct S3 URL should be blocked ❌ (403 Forbidden)

## Troubleshooting

If you still see 403 errors:

1. **Check CloudFront distribution status**: Must be "Deployed"
2. **Verify Origin Access Control**: Check S3 bucket policy has correct CloudFront ARN
3. **Cache issues**: Wait for invalidation to complete or try incognito mode
4. **DNS propagation**: If using custom domain, allow time for DNS changes

## Architecture Benefits
- **Security**: S3 bucket remains private, only accessible via CloudFront
- **Performance**: CloudFront CDN provides global edge caching
- **Cost**: More efficient than public S3 website hosting
- **Features**: HTTPS by default, compression, custom error pages