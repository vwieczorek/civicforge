# Backend Architecture

*Last Updated: January 2025*

## Overview

The CivicForge backend is built on a serverless architecture using AWS Lambda, FastAPI, and DynamoDB. It follows a security-first approach with granular Lambda functions for different operations and uses dependency injection for better testability and maintainability.

## Architecture Principles

### 1. Lambda-per-Operation Pattern

Instead of a monolithic API, we use separate Lambda functions for critical operations:

- **`api`**: Read-only operations (GET endpoints)
- **`createQuest`**: Quest creation with point deduction
- **`attestQuest`**: Quest attestation and completion
- **`deleteQuest`**: Quest deletion
- **`createUserTrigger`**: Cognito post-confirmation trigger

Each function has its own IAM role with minimal permissions, following the principle of least privilege.

### 2. Dependency Injection

We use FastAPI's dependency injection system to manage database connections and other dependencies:

```python
from fastapi import Depends
from src.db import get_db_client, DynamoDBClient

@router.post("/quests")
async def create_quest(
    quest: QuestCreate,
    user_id: str = Depends(get_current_user_id),
    db: DynamoDBClient = Depends(get_db_client)
) -> Quest:
    # Use the injected db client
    await db.create_quest(quest)
```

This pattern provides:
- Better testability (easy to mock dependencies)
- Cleaner code organization
- Proper resource lifecycle management

### 3. Application Factory Pattern

Each Lambda handler creates its own FastAPI application instance using the `app_factory`:

```python
from src.app_factory import create_app
from src.routers.quests_create import router

# In the Lambda handler
app = create_app(
    routers=[router],
    title="Quest Creation API",
    description="Handles quest creation"
)
```

## Core Components

### Database Layer (`src/db.py`)

The `DynamoDBClient` class handles all database operations:

- **Atomic Operations**: Uses DynamoDB condition expressions to prevent race conditions
- **Error Handling**: Gracefully handles AWS service errors
- **Serialization**: Custom serialization for Python/DynamoDB type conversion

Key methods:
- `claim_quest_atomic()`: Atomically claims a quest
- `add_attestation_atomic()`: Prevents duplicate attestations
- `complete_quest_atomic()`: Ensures quest completion happens exactly once

### State Machine (`src/state_machine.py`)

The `QuestStateMachine` class encapsulates all business logic for quest state transitions:

```python
class QuestStateMachine:
    @staticmethod
    def can_user_claim(quest: Quest, user_id: str) -> bool:
        # Business logic for claim authorization
        
    @staticmethod
    def is_ready_for_completion(quest: Quest) -> bool:
        # Checks if dual attestation is complete
```

### Authentication (`src/auth.py`)

JWT-based authentication using AWS Cognito:

- Verifies tokens against Cognito's public keys
- Caches keys for performance
- Provides FastAPI dependencies for auth requirements

### Models (`src/models.py`)

Pydantic models for:
- Request/response validation
- Data serialization
- Business rule enforcement (e.g., HTML sanitization)

## Request Flow

1. **API Gateway** receives request
2. **Lambda function** is invoked based on the route
3. **FastAPI app** handles routing and validation
4. **Authentication** verifies JWT token
5. **Business logic** in routers processes the request
6. **State machine** validates state transitions
7. **Database client** performs atomic operations
8. **Response** is serialized and returned

## Error Handling

### Retry Logic

Critical operations implement retry logic with exponential backoff:

```python
async def award_rewards(self, user_id: str, xp: int, reputation: int):
    for attempt in range(3):
        try:
            # Attempt operation
            break
        except ClientError:
            if attempt == 2:
                # Track failed reward for later processing
                await self.track_failed_reward(...)
```

### Dead Letter Queues

Failed operations are sent to DLQs for later processing:
- `UserCreationDLQ`: Failed user creation events
- Failed rewards are tracked in the `FailedRewards` table

### Monitoring

- AWS X-Ray tracing enabled for distributed debugging
- CloudWatch alarms for error rates and DLQ messages
- Custom metrics for business events

## Testing Strategy

### Integration Tests Preferred

Tests use real service behavior with mocked AWS infrastructure:

```python
async def test_quest_lifecycle(authenticated_client):
    # This test uses:
    # - Real FastAPI app instance
    # - Real DynamoDB client code
    # - Mocked AWS services (via moto)
    response = await authenticated_client.post("/api/v1/quests", ...)
```

### Minimal Mocking

We avoid mocking our own code. Instead:
- Use `moto` for AWS service mocking
- Use dependency injection to provide test instances
- Test complete request/response cycles

## Security Considerations

### IAM Roles

Each Lambda function has a specific IAM role:

```yaml
# Example: createQuest function
iamRoleStatements:
  - Effect: Allow
    Action:
      - dynamodb:PutItem
    Resource: !GetAtt QuestsTable.Arn
  - Effect: Allow
    Action:
      - dynamodb:UpdateItem
    Resource: !GetAtt UsersTable.Arn
    Condition:
      ForAllValues:StringEquals:
        dynamodb:Attributes: [questCreationPoints]
```

### Input Validation

- Pydantic models validate all inputs
- HTML content is sanitized using `bleach`
- Ethereum addresses are validated with checksum verification

### Atomic Operations

All state-changing operations use DynamoDB condition expressions to ensure consistency and prevent race conditions.

## Future Considerations

### Scaling

- DynamoDB on-demand scaling handles traffic spikes
- Lambda concurrency limits may need adjustment
- Consider caching for frequently accessed data

### Feature Additions

New features should:
1. Follow the Lambda-per-operation pattern for critical operations
2. Use the existing state machine for business logic
3. Implement proper error handling and monitoring
4. Include comprehensive integration tests