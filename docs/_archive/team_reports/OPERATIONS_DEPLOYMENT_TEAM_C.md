# Team C: Operations & Deployment Guide

## Overview

Team C is responsible for creating the safety net for MVP deployment through feature flags, performance optimizations, and deployment infrastructure. This team also provides critical support to Team B for E2E test environment setup.

## Priority 0: Support Team B E2E Setup (Day 1)

### Immediate Actions

1. **Verify Local Development Environment**

```bash
# Check all required services are running
cd backend && npm run dev  # Should start on port 3001
cd frontend && npm run dev # Should start on port 5173

# Verify API is accessible
curl http://localhost:3001/api/v1/health
```

2. **Create Docker Compose for E2E Testing**

Create `docker-compose.e2e.yml`:

```yaml
version: '3.8'

services:
  localstack:
    image: localstack/localstack:latest
    environment:
      - SERVICES=dynamodb,cognito,ssm
      - DEBUG=1
      - DATA_DIR=/tmp/localstack/data
    ports:
      - "4566:4566"
    volumes:
      - "${TMPDIR:-/tmp}/localstack:/tmp/localstack"
      - "/var/run/docker.sock:/var/run/docker.sock"

  backend:
    build: ./backend
    environment:
      - AWS_ENDPOINT_URL=http://localstack:4566
      - DYNAMODB_ENDPOINT=http://localstack:4566
      - COGNITO_USER_POOL_ID=test-pool-id
      - COGNITO_CLIENT_ID=test-client-id
      - NODE_ENV=test
    ports:
      - "3001:3001"
    depends_on:
      - localstack
    command: npm run dev:test

  frontend:
    build: ./frontend
    environment:
      - VITE_API_BASE_URL=http://localhost:3001
      - VITE_COGNITO_USER_POOL_ID=test-pool-id
      - VITE_COGNITO_CLIENT_ID=test-client-id
    ports:
      - "5173:5173"
    depends_on:
      - backend
```

3. **Create E2E Test Bootstrap Script**

Create `scripts/setup-e2e-env.sh`:

```bash
#!/bin/bash
set -e

echo "Setting up E2E test environment..."

# Start services
docker-compose -f docker-compose.e2e.yml up -d

# Wait for LocalStack
echo "Waiting for LocalStack..."
until aws --endpoint-url=http://localhost:4566 dynamodb list-tables 2>/dev/null; do
  sleep 2
done

# Create test tables
aws --endpoint-url=http://localhost:4566 dynamodb create-table \
  --table-name civicforge-users-test \
  --attribute-definitions AttributeName=userId,AttributeType=S \
  --key-schema AttributeName=userId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws --endpoint-url=http://localhost:4566 dynamodb create-table \
  --table-name civicforge-quests-test \
  --attribute-definitions AttributeName=questId,AttributeType=S \
  --key-schema AttributeName=questId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Create test Cognito user pool
aws --endpoint-url=http://localhost:4566 cognito-idp create-user-pool \
  --pool-name civicforge-test-pool

echo "E2E environment ready!"
```

## Priority 1: Feature Flag System (Day 1-2)

### 1.1 Implement AWS AppConfig Integration

Create `backend/src/feature_flags_v2.py`:

```python
"""
Enhanced feature flag system using AWS AppConfig
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
import hashlib

logger = logging.getLogger(__name__)

class FeatureFlagService:
    """
    Feature flag service with AWS AppConfig integration
    """
    
    def __init__(self):
        self.app_config_client = boto3.client('appconfig')
        self.app_id = os.environ.get('APPCONFIG_APPLICATION_ID', 'civicforge')
        self.env_id = os.environ.get('APPCONFIG_ENVIRONMENT_ID', 'production')
        self.config_profile_id = os.environ.get('APPCONFIG_PROFILE_ID', 'feature-flags')
        self._cache = {}
        self._cache_expiry = {}
        self.cache_duration = timedelta(minutes=5)
    
    def get_flags(self, user_id: Optional[str] = None) -> Dict[str, bool]:
        """
        Get all feature flags for a user
        """
        cache_key = f"flags_{user_id or 'default'}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            # Fetch from AppConfig
            response = self.app_config_client.get_configuration(
                Application=self.app_id,
                Environment=self.env_id,
                Configuration=self.config_profile_id,
                ClientId=user_id or 'anonymous'
            )
            
            # Parse configuration
            config_data = json.loads(response['Content'].read())
            flags = self._evaluate_flags(config_data, user_id)
            
            # Cache results
            self._cache[cache_key] = flags
            self._cache_expiry[cache_key] = datetime.utcnow() + self.cache_duration
            
            return flags
            
        except Exception as e:
            logger.error(f"Failed to fetch feature flags: {str(e)}")
            # Return safe defaults
            return self._get_default_flags()
    
    def is_enabled(self, flag_name: str, user_id: Optional[str] = None) -> bool:
        """
        Check if a specific feature flag is enabled
        """
        flags = self.get_flags(user_id)
        return flags.get(flag_name, False)
    
    def _evaluate_flags(self, config: Dict[str, Any], user_id: Optional[str]) -> Dict[str, bool]:
        """
        Evaluate feature flags based on rules
        """
        evaluated = {}
        
        for flag_name, flag_config in config.get('flags', {}).items():
            # Check if globally enabled
            if flag_config.get('enabled', False):
                evaluated[flag_name] = True
                continue
            
            # Check percentage rollout
            if user_id and 'rollout_percentage' in flag_config:
                percentage = flag_config['rollout_percentage']
                if self._is_in_rollout(user_id, flag_name, percentage):
                    evaluated[flag_name] = True
                    continue
            
            # Check user whitelist
            if user_id and user_id in flag_config.get('whitelist_users', []):
                evaluated[flag_name] = True
                continue
            
            # Default to disabled
            evaluated[flag_name] = False
        
        return evaluated
    
    def _is_in_rollout(self, user_id: str, flag_name: str, percentage: int) -> bool:
        """
        Determine if user is in percentage rollout
        """
        # Create stable hash for user + flag combination
        hash_input = f"{user_id}:{flag_name}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        # Map to 0-100 range
        user_bucket = hash_value % 100
        
        return user_bucket < percentage
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Check if cached data is still valid
        """
        if cache_key not in self._cache:
            return False
        
        expiry = self._cache_expiry.get(cache_key)
        return expiry and datetime.utcnow() < expiry
    
    def _get_default_flags(self) -> Dict[str, bool]:
        """
        Return safe default flags when service is unavailable
        """
        return {
            'dual_attestation': True,  # Core feature always on
            'wallet_integration': False,  # New feature off by default
            'quest_categories': False,  # New feature off by default
            'advanced_search': False,  # New feature off by default
        }

# Global instance
feature_flags = FeatureFlagService()
```

### 1.2 Create Frontend Feature Flag Hook

Create `frontend/src/hooks/useFeatureFlags.ts`:

```typescript
import { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';

interface FeatureFlags {
  dual_attestation: boolean;
  wallet_integration: boolean;
  quest_categories: boolean;
  advanced_search: boolean;
}

const DEFAULT_FLAGS: FeatureFlags = {
  dual_attestation: true,
  wallet_integration: false,
  quest_categories: false,
  advanced_search: false,
};

export function useFeatureFlags() {
  const [flags, setFlags] = useState<FeatureFlags>(DEFAULT_FLAGS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchFlags = async () => {
      try {
        const response = await apiClient.get<FeatureFlags>('/api/v1/feature-flags');
        setFlags(response);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch feature flags:', err);
        setError(err as Error);
        // Use defaults on error
      } finally {
        setLoading(false);
      }
    };

    fetchFlags();
    
    // Refresh flags periodically
    const interval = setInterval(fetchFlags, 5 * 60 * 1000); // 5 minutes
    
    return () => clearInterval(interval);
  }, []);

  const isEnabled = (flagName: keyof FeatureFlags): boolean => {
    return flags[flagName] ?? DEFAULT_FLAGS[flagName];
  };

  return { flags, isEnabled, loading, error };
}

// Feature flag protected component
export function FeatureFlag({ 
  name, 
  children, 
  fallback = null 
}: { 
  name: keyof FeatureFlags;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { isEnabled } = useFeatureFlags();
  
  return isEnabled(name) ? <>{children}</> : <>{fallback}</>;
}
```

### 1.3 AWS AppConfig Configuration

Create `infrastructure/appconfig-flags.json`:

```json
{
  "flags": {
    "dual_attestation": {
      "enabled": true,
      "description": "Core dual attestation feature"
    },
    "wallet_integration": {
      "enabled": false,
      "rollout_percentage": 0,
      "whitelist_users": ["admin-user-1", "tester-user-1"],
      "description": "Ethereum wallet integration for signatures"
    },
    "quest_categories": {
      "enabled": false,
      "rollout_percentage": 10,
      "description": "Quest categorization feature"
    },
    "advanced_search": {
      "enabled": false,
      "rollout_percentage": 0,
      "description": "Advanced quest search functionality"
    }
  },
  "rollout_stages": {
    "stage_1_internal": {
      "wallet_integration": { "whitelist_users": ["internal-users"] },
      "quest_categories": { "whitelist_users": ["internal-users"] }
    },
    "stage_2_beta": {
      "wallet_integration": { "rollout_percentage": 10 },
      "quest_categories": { "rollout_percentage": 25 }
    },
    "stage_3_ga": {
      "wallet_integration": { "rollout_percentage": 100 },
      "quest_categories": { "rollout_percentage": 100 }
    }
  }
}
```

## Priority 2: Lambda Performance Optimization (Day 2-3)

### 2.1 DynamoDB Client Optimization

Create `backend/src/optimized_db.py`:

```python
"""
Optimized DynamoDB client with connection reuse
"""
import os
import boto3
from typing import Optional
import aiobotocore.session

# Initialize clients outside handler for reuse
_sync_dynamodb_resource = None
_async_session = None

def get_sync_dynamodb_resource():
    """Get or create singleton sync DynamoDB resource"""
    global _sync_dynamodb_resource
    
    if _sync_dynamodb_resource is None:
        if os.environ.get('AWS_SAM_LOCAL'):
            # Local development
            _sync_dynamodb_resource = boto3.resource(
                'dynamodb',
                endpoint_url='http://localhost:8000'
            )
        else:
            # Production - reuse connection
            _sync_dynamodb_resource = boto3.resource('dynamodb')
    
    return _sync_dynamodb_resource

async def get_async_dynamodb_resource():
    """Get or create singleton async DynamoDB resource"""
    global _async_session
    
    if _async_session is None:
        _async_session = aiobotocore.session.get_session()
    
    # Create resource from session
    async with _async_session.create_client('dynamodb') as client:
        return client

# Update all Lambda handlers to use these optimized clients
```

### 2.2 Lambda Handler Optimization Template

Create `backend/handlers/optimized_handler_template.py`:

```python
"""
Template for optimized Lambda handlers
"""
import json
import os
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3

# Initialize AWS clients outside handler
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(os.environ['USERS_TABLE'])
quests_table = dynamodb.Table(os.environ['QUESTS_TABLE'])

# Initialize Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Pre-compile any regex patterns, load configs, etc.
ALLOWED_STATUSES = {'ACTIVE', 'CLAIMED', 'SUBMITTED', 'COMPLETED'}

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Optimized Lambda handler with connection reuse
    """
    try:
        # Add custom metrics
        metrics.add_metric(name="RequestCount", unit=MetricUnit.Count, value=1)
        
        # Process request
        # ... handler logic ...
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success'})
        }
        
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        metrics.add_metric(name="ErrorCount", unit=MetricUnit.Count, value=1)
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
```

### 2.3 Provisioned Concurrency Configuration

Update `backend/serverless.yml`:

```yaml
custom:
  # Provisioned concurrency for critical endpoints
  provisionedConcurrency:
    prod:
      attestQuest: 2
      createQuest: 1
      getQuest: 2
    staging:
      attestQuest: 1
      createQuest: 1

functions:
  attestQuest:
    handler: handlers.attest_quest.handler
    provisionedConcurrency: ${self:custom.provisionedConcurrency.${self:provider.stage}.attestQuest, 0}
    events:
      - httpApi:
          path: /api/v1/quests/{quest_id}/attest
          method: POST
```

## Priority 3: Monitoring & Observability (Day 3-4)

### 3.1 CloudWatch Dashboard Configuration

Create `infrastructure/cloudwatch-dashboard.json`:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Duration", {"stat": "Average"}],
          [".", ".", {"stat": "p99"}],
          ["AWS/Lambda", "Errors", {"stat": "Sum"}],
          ["AWS/Lambda", "Throttles", {"stat": "Sum"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Lambda Performance"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/DynamoDB", "ConsumedReadCapacityUnits", {"stat": "Sum"}],
          [".", "ConsumedWriteCapacityUnits", {"stat": "Sum"}],
          [".", "ThrottledRequests", {"stat": "Sum"}]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "DynamoDB Usage"
      }
    },
    {
      "type": "log",
      "properties": {
        "query": "SOURCE '/aws/lambda/civicforge-prod-attestQuest'\n| fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 20",
        "region": "us-east-1",
        "title": "Recent Errors"
      }
    }
  ]
}
```

### 3.2 Create Deployment Script with Canary Support

Create `scripts/deploy-with-canary.sh`:

```bash
#!/bin/bash
set -e

STAGE=${1:-staging}
CANARY_PERCENTAGE=${2:-10}

echo "Deploying CivicForge to $STAGE with $CANARY_PERCENTAGE% canary..."

# Check prerequisites
./scripts/check-mvp-readiness.sh
if [ $? -ne 0 ]; then
    echo "MVP readiness check failed. Aborting deployment."
    exit 1
fi

# Deploy backend with alias
cd backend
serverless deploy --stage $STAGE

# Create canary alias
aws lambda update-alias \
  --function-name civicforge-$STAGE-attestQuest \
  --name live \
  --function-version \$LATEST \
  --routing-config AdditionalVersionWeights={"\$LATEST"=$CANARY_PERCENTAGE}

# Deploy frontend
cd ../frontend
npm run build
aws s3 sync dist/ s3://civicforge-$STAGE-frontend/ --delete

# Update CloudFront distribution
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_ID \
  --paths "/*"

echo "Deployment complete. Monitoring canary deployment..."

# Monitor for 10 minutes
for i in {1..20}; do
    echo "Checking metrics (${i}/20)..."
    
    ERROR_COUNT=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/Lambda \
        --metric-name Errors \
        --dimensions Name=FunctionName,Value=civicforge-$STAGE-attestQuest \
        --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
        --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
        --period 300 \
        --statistics Sum \
        --query 'Datapoints[0].Sum' \
        --output text)
    
    if [ "$ERROR_COUNT" != "None" ] && [ "$ERROR_COUNT" -gt "5" ]; then
        echo "High error rate detected! Rolling back..."
        ./scripts/rollback.sh $STAGE
        exit 1
    fi
    
    sleep 30
done

echo "Canary deployment successful. Promoting to 100%..."

# Promote canary to 100%
aws lambda update-alias \
  --function-name civicforge-$STAGE-attestQuest \
  --name live \
  --function-version \$LATEST

echo "Deployment complete!"
```

## Priority 4: Rollback Procedures (Day 4)

### 4.1 Create Rollback Script

Create `scripts/rollback.sh`:

```bash
#!/bin/bash
set -e

STAGE=${1:-staging}
echo "Rolling back CivicForge $STAGE deployment..."

# Get previous version
PREVIOUS_VERSION=$(aws lambda get-alias \
  --function-name civicforge-$STAGE-attestQuest \
  --name live \
  --query 'AliasArn' \
  --output text | grep -oE '[0-9]+$')

# Rollback Lambda aliases
FUNCTIONS=(attestQuest createQuest getQuest listQuests)
for func in "${FUNCTIONS[@]}"; do
    echo "Rolling back $func..."
    aws lambda update-alias \
      --function-name civicforge-$STAGE-$func \
      --name live \
      --function-version $((PREVIOUS_VERSION - 1))
done

# Rollback frontend (requires S3 versioning enabled)
echo "Rolling back frontend..."
aws s3api list-object-versions \
  --bucket civicforge-$STAGE-frontend \
  --prefix index.html \
  --max-items 2 \
  --query 'Versions[1].VersionId' \
  --output text | xargs -I {} \
  aws s3api copy-object \
    --bucket civicforge-$STAGE-frontend \
    --copy-source civicforge-$STAGE-frontend/index.html?versionId={} \
    --key index.html

# Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_ID \
  --paths "/*"

# Alert team
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:123456789012:civicforge-alerts \
  --message "Rollback completed for $STAGE environment"

echo "Rollback complete!"
```

## Team C Checklist

### Day 1
- [ ] Docker Compose E2E environment created
- [ ] E2E bootstrap script working
- [ ] Team B unblocked on E2E setup
- [ ] Feature flag service implemented

### Day 2
- [ ] AWS AppConfig integrated
- [ ] Frontend feature flag hook created
- [ ] Lambda client optimization implemented
- [ ] Performance improvements measurable

### Day 3
- [ ] CloudWatch dashboard configured
- [ ] Canary deployment script created
- [ ] Monitoring alerts set up
- [ ] Deployment procedures documented

### Day 4
- [ ] Rollback script tested
- [ ] Full deployment pipeline validated
- [ ] Team handoff documentation complete
- [ ] Production readiness confirmed

## Success Criteria

1. **E2E tests running** in isolated environment
2. **Feature flags controlling** attestation feature
3. **Lambda cold starts reduced** by 30%+ 
4. **Canary deployments** with automatic rollback
5. **Complete observability** of production systems

## Communication Points

- Daily sync with Team B on E2E environment
- API contract alignment with Team A
- Performance metrics shared with all teams
- Deployment status in #civicforge-mvp channel