# AWS Lambda Powertools Idempotency Guide

This guide explains how to use AWS Lambda Powertools idempotency features in CivicForge to ensure operations are executed exactly once, even with retries.

## Overview

Idempotency is crucial for:
- Financial operations (quest creation, rewards)
- User creation and updates
- State transitions (quest status changes)
- External API calls

## Setup

The idempotency infrastructure is automatically configured:

1. **DynamoDB Table**: `civicforge-{stage}-idempotency`
2. **TTL**: Automatic expiration of idempotency records
3. **IAM Permissions**: Automatically granted to all Lambda functions

## Basic Usage

### 1. Lambda Handler Idempotency

Make entire Lambda handlers idempotent:

```python
from src.utils.idempotency import make_idempotent

@make_idempotent(event_key_jmespath="body.questId")
def handler(event, context):
    # This handler will only execute once per unique questId
    quest = create_quest(event['body'])
    return {
        'statusCode': 200,
        'body': json.dumps(quest)
    }
```

### 2. Function-Level Idempotency

Make individual functions idempotent:

```python
from src.utils.idempotency import make_idempotent_function

@make_idempotent_function(data_keyword_argument="quest_id")
async def award_quest_rewards(quest_id: str, user_id: str, rewards: dict):
    # This function will only execute once per unique quest_id
    await user_repo.award_rewards(user_id, rewards['xp'], rewards['reputation'])
    return {"status": "rewards_awarded"}
```

### 3. Context Manager for Complex Logic

For more control, use the IdempotencyHandler:

```python
from src.utils.idempotency import IdempotencyHandler

async def process_attestation(quest_id: str, user_id: str, attestation_data: dict):
    idempotency_key = f"attestation-{quest_id}-{user_id}"
    
    async with IdempotencyHandler(idempotency_key, expires_after_seconds=86400) as handler:
        if handler.is_cached:
            # Return cached result from previous execution
            return handler.cached_result
        
        # Process attestation
        result = await quest_repo.add_attestation(
            quest_id, user_id, attestation_data
        )
        
        # Check if rewards should be distributed
        if result.both_attestations_complete:
            await distribute_rewards(quest_id)
        
        # Save result for future idempotent calls
        response = {"status": "success", "quest_id": quest_id}
        handler.save_result(response)
        
        return response
```

## Pre-configured Decorators

CivicForge provides pre-configured decorators for common operations:

### Quest Creation
```python
from src.utils.idempotency import quest_creation_idempotent

@quest_creation_idempotent  # 24-hour idempotency on questId
def create_quest_handler(event, context):
    # Implementation
```

### Reward Processing
```python
from src.utils.idempotency import reward_processing_idempotent

@reward_processing_idempotent  # 7-day idempotency on rewardId
def process_failed_reward_handler(event, context):
    # Implementation
```

### User Creation
```python
from src.utils.idempotency import user_creation_idempotent

@user_creation_idempotent  # 1-hour idempotency on userId
def create_user_handler(event, context):
    # Implementation
```

### Attestation
```python
from src.utils.idempotency import attestation_idempotent

@attestation_idempotent  # 24-hour idempotency on [questId, userId]
def attest_quest_handler(event, context):
    # Implementation
```

## JMESPath Key Extraction

Idempotency keys are extracted using JMESPath expressions:

| Event Type | JMESPath | Example Key |
|------------|----------|-------------|
| API Gateway | `body.questId` | Quest ID from request body |
| SQS | `Records[0].body.transactionId` | Transaction ID from SQS message |
| SNS | `Records[0].Sns.MessageAttributes.orderId.Value` | Order ID from SNS attributes |
| Cognito | `request.userAttributes.sub` | User ID from Cognito event |
| Composite | `[body.questId, body.userId]` | Combined quest and user ID |

## Error Handling

### Idempotency Already In Progress

When a request is already being processed:

```python
from aws_lambda_powertools.utilities.idempotency.exceptions import IdempotencyAlreadyInProgressError

try:
    result = process_payment(payment_id)
except IdempotencyAlreadyInProgressError:
    # Another Lambda is processing this payment
    return {
        'statusCode': 409,
        'body': json.dumps({
            'error': 'Payment already being processed'
        })
    }
```

### Idempotency Item Already Exists

When a request was already processed:

```python
from aws_lambda_powertools.utilities.idempotency.exceptions import IdempotencyItemAlreadyExistsError

try:
    result = create_resource(resource_id)
except IdempotencyItemAlreadyExistsError as e:
    # Return the previous result
    return e.old_data_record
```

## Best Practices

### 1. Choose Appropriate Expiration Times

```python
# Short-lived operations (API requests)
@make_idempotent(expires_after_seconds=300)  # 5 minutes

# Long-lived operations (async workflows)
@make_idempotent(expires_after_seconds=86400)  # 24 hours

# Critical financial operations
@make_idempotent(expires_after_seconds=604800)  # 7 days
```

### 2. Use Meaningful Idempotency Keys

```python
# Good: Includes context
@make_idempotent(event_key_jmespath="[body.userId, body.questId, body.action]")

# Bad: Too generic
@make_idempotent(event_key_jmespath="body.id")
```

### 3. Handle Partial Failures

```python
async def process_complex_operation(data):
    async with IdempotencyHandler(f"operation-{data['id']}") as handler:
        if handler.is_cached:
            return handler.cached_result
        
        try:
            # Step 1
            result1 = await step1(data)
            
            # Step 2
            result2 = await step2(result1)
            
            # Step 3
            final_result = await step3(result2)
            
            handler.save_result(final_result)
            return final_result
            
        except Exception as e:
            # Idempotency record will be deleted on exit
            logger.error(f"Operation failed: {e}")
            raise
```

### 4. Combine with DynamoDB Conditional Writes

```python
@quest_creation_idempotent
async def create_quest_handler(event, context):
    # Idempotency prevents duplicate Lambda executions
    quest_data = json.loads(event['body'])
    
    # DynamoDB conditional write prevents duplicate records
    try:
        quest = await quest_repo.create_quest(quest_data)
        return {'statusCode': 201, 'body': json.dumps(quest)}
    except ConditionalCheckFailedException:
        # Quest already exists (race condition)
        existing = await quest_repo.get_by_id(quest_data['questId'])
        return {'statusCode': 200, 'body': json.dumps(existing)}
```

## Testing Idempotency

### Unit Tests

```python
import pytest
from moto import mock_dynamodb
from aws_lambda_powertools.utilities.idempotency import IdempotencyConfig

@mock_dynamodb
def test_idempotent_handler():
    # First call - should execute
    result1 = handler({'body': {'questId': '123'}}, {})
    assert result1['statusCode'] == 200
    
    # Second call - should return cached result
    result2 = handler({'body': {'questId': '123'}}, {})
    assert result2 == result1
    
    # Different ID - should execute
    result3 = handler({'body': {'questId': '456'}}, {})
    assert result3['statusCode'] == 200
```

### Integration Tests

```python
def test_concurrent_requests():
    # Simulate concurrent Lambda invocations
    import concurrent.futures
    
    quest_id = str(uuid.uuid4())
    event = {'body': {'questId': quest_id}}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(handler, event, {})
            for _ in range(5)
        ]
        
        results = [f.result() for f in futures]
    
    # All results should be identical
    assert all(r == results[0] for r in results)
    
    # Quest should only be created once
    quests = get_quests_by_id(quest_id)
    assert len(quests) == 1
```

## Monitoring

### CloudWatch Metrics

Idempotency operations are automatically logged:

```python
# Structured logs
{
    "level": "INFO",
    "message": "idempotency_cache_hit",
    "idempotency_key": "quest-123",
    "service": "civicforge",
    "timestamp": "2024-01-01T00:00:00Z"
}
```

### X-Ray Tracing

Idempotency operations are traced:
- Cache hits/misses
- DynamoDB operations
- Execution time savings

## Migration Guide

### Existing Handlers

Before:
```python
def handler(event, context):
    quest_id = event['body']['questId']
    
    # Manual idempotency check
    existing = get_quest(quest_id)
    if existing:
        return format_response(existing)
    
    # Create quest
    quest = create_quest(event['body'])
    return format_response(quest)
```

After:
```python
@quest_creation_idempotent
def handler(event, context):
    # Idempotency handled automatically
    quest = create_quest(event['body'])
    return format_response(quest)
```

### Distributed Locking

Replace custom locking with idempotency:

Before:
```python
def process_reward(reward_id):
    if not acquire_lock(reward_id):
        return "Already processing"
    
    try:
        # Process reward
        result = do_work()
        return result
    finally:
        release_lock(reward_id)
```

After:
```python
@make_idempotent(event_key_jmespath="rewardId")
def process_reward(event, context):
    # Locking handled automatically
    result = do_work()
    return result
```

## Troubleshooting

### Common Issues

1. **"Idempotency table not found"**
   - Ensure the table is created in your CloudFormation/Serverless template
   - Check IAM permissions include the idempotency table

2. **"Cannot extract idempotency key"**
   - Verify your JMESPath expression matches the event structure
   - Test with: `jmespath.search(expression, event)`

3. **"Idempotency record expired"**
   - Increase `expires_after_seconds` for long-running operations
   - Consider if idempotency is appropriate for this use case

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger("aws_lambda_powertools").setLevel(logging.DEBUG)
```

## Performance Considerations

1. **Local Cache**: Reduces DynamoDB calls within same Lambda container
2. **TTL**: Automatic cleanup prevents table growth
3. **Compression**: Large payloads are automatically compressed
4. **Batch Operations**: Not suitable for batch processing - use per-item idempotency

## Security

1. **Encryption**: Idempotency table uses KMS encryption
2. **IAM**: Least privilege access to idempotency table
3. **Data Retention**: Set appropriate TTL for compliance
4. **PII**: Avoid storing sensitive data in idempotency keys