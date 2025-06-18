# Repository Pattern Migration Guide

This guide explains how to migrate from the existing `db.py` module to the new repository pattern implementation.

## Benefits of Repository Pattern

1. **Centralized Data Access**: All DynamoDB operations for an entity are in one place
2. **Built-in Safety**: Automatic error handling, logging, and retry logic
3. **Consistent Patterns**: Enforces best practices across all data access
4. **Easier Testing**: Mock repositories instead of DynamoDB directly
5. **Type Safety**: Full type hints for all operations
6. **Separation of Concerns**: Business logic separated from data access

## Migration Examples

### Before (using db.py)

```python
# In routers/users.py
from ..db import get_user, award_rewards

async def get_user_endpoint(user_id: str):
    user = await get_user(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return user

async def award_rewards_endpoint(user_id: str, xp: int, rep: int):
    try:
        await award_rewards(user_id, xp, rep)
    except Exception as e:
        logger.error(f"Failed to award rewards: {e}")
        raise HTTPException(status_code=500)
```

### After (using repositories)

```python
# In routers/users.py
from ..repositories import UserRepository

user_repo = UserRepository()

async def get_user_endpoint(user_id: str):
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return user

async def award_rewards_endpoint(user_id: str, xp: int, rep: int):
    success = await user_repo.award_rewards(user_id, xp, rep)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to award rewards")
```

## Function Mapping

### User Operations

| Old Function (db.py) | New Method (UserRepository) | Notes |
|---------------------|---------------------------|--------|
| `get_user(user_id)` | `user_repo.get_by_id(user_id)` | Returns User model |
| `create_user(user)` | `user_repo.create_user(user)` | Idempotent |
| `award_rewards(user_id, xp, rep)` | `user_repo.award_rewards(user_id, xp, rep)` | Returns bool |
| `deduct_quest_creation_points(user_id, points)` | `user_repo.deduct_quest_points(user_id, points)` | Checks balance |
| `update_wallet_address(user_id, addr)` | `user_repo.update_wallet_address(user_id, addr)` | |
| `award_quest_creation_points(user_id, points)` | `user_repo.award_quest_points(user_id, points)` | For refunds |

### Quest Operations

| Old Function (db.py) | New Method (QuestRepository) | Notes |
|---------------------|---------------------------|--------|
| `get_quest(quest_id)` | `quest_repo.get_by_id(quest_id)` | Returns Quest model |
| `get_quest_for_update(quest_id)` | `quest_repo.get_for_update(quest_id)` | Strong consistency |
| `create_quest(quest)` | `quest_repo.create_quest(quest)` | |
| `update_quest(quest)` | `quest_repo.update_quest(quest)` | Full replacement |
| `list_quests(status, limit, start)` | `quest_repo.list_by_status(status, limit, start)` | Uses GSI only |
| `get_user_created_quests(user_id, ...)` | `quest_repo.get_user_quests(user_id, 'creator', ...)` | |
| `get_user_performed_quests(user_id, ...)` | `quest_repo.get_user_quests(user_id, 'performer', ...)` | |
| `claim_quest_atomically(quest_id, user_id)` | `quest_repo.claim_quest(quest_id, user_id)` | Returns bool |
| `submit_quest_atomically(quest_id, user_id, text)` | `quest_repo.submit_quest(quest_id, user_id, text)` | Returns bool |
| `add_attestation_atomically(...)` | `quest_repo.add_attestation(...)` | Prevents duplicates |
| `complete_quest_atomically(quest_id)` | `quest_repo.complete_quest(quest_id)` | Checks attestations |
| `delete_quest_atomically(quest_id, user_id)` | `quest_repo.delete_quest(quest_id, user_id)` | Creator only |
| `dispute_quest_atomically(...)` | `quest_repo.dispute_quest(...)` | Involved parties only |

### Failed Reward Operations

| Old Function (db.py) | New Method (FailedRewardRepository) | Notes |
|---------------------|---------------------------|--------|
| `track_failed_reward(...)` | `failed_repo.track_failed_reward(...)` | Returns record_id |
| `get_pending_failed_rewards(limit, start)` | `failed_repo.get_pending_rewards(limit, start)` | |
| `mark_reward_completed(record_id)` | `failed_repo.mark_completed(record_id)` | |
| N/A | `failed_repo.acquire_processing_lease(record_id, owner)` | Distributed lock |
| N/A | `failed_repo.release_lease(record_id, owner)` | |
| N/A | `failed_repo.update_status(...)` | Flexible status update |

## Step-by-Step Migration

### 1. Update Imports

Replace all imports from `db` module:

```python
# Before
from ..db import get_user, create_quest, award_rewards

# After
from ..repositories import UserRepository, QuestRepository

# Initialize repositories
user_repo = UserRepository()
quest_repo = QuestRepository()
```

### 2. Update Function Calls

Most functions have direct equivalents with similar signatures:

```python
# Before
user = await get_user(user_id)
quest = await get_quest(quest_id)

# After
user = await user_repo.get_by_id(user_id)
quest = await quest_repo.get_by_id(quest_id)
```

### 3. Handle Return Value Changes

Some functions now return booleans instead of raising exceptions:

```python
# Before
try:
    await claim_quest_atomically(quest_id, user_id)
except ConditionalCheckFailedException:
    raise HTTPException(status_code=409, detail="Quest already claimed")

# After
success = await quest_repo.claim_quest(quest_id, user_id)
if not success:
    raise HTTPException(status_code=409, detail="Quest already claimed")
```

### 4. Update Error Handling

Repositories handle most errors internally and log them:

```python
# Before
try:
    await award_rewards(user_id, xp, rep)
except ClientError as e:
    logger.error(f"DynamoDB error: {e}")
    raise HTTPException(status_code=500)

# After
success = await user_repo.award_rewards(user_id, xp, rep)
if not success:
    # Error already logged by repository
    raise HTTPException(status_code=500, detail="Failed to award rewards")
```

### 5. Update Tests

Mock repositories instead of DynamoDB:

```python
# Before
@patch('backend.src.db.dynamodb')
def test_get_user(mock_dynamodb):
    mock_table = Mock()
    mock_dynamodb.Table.return_value = mock_table
    # ... complex mocking

# After
@patch('backend.src.repositories.user_repository.UserRepository.get_by_id')
async def test_get_user(mock_get_by_id):
    mock_get_by_id.return_value = User(userId="123", username="test")
    # ... simpler mocking
```

## Testing the Migration

1. **Run existing tests** to ensure compatibility
2. **Update integration tests** to use repositories
3. **Test error scenarios** (e.g., insufficient balance, double claiming)
4. **Monitor logs** for proper structured logging
5. **Verify metrics** are being recorded

## Rollback Plan

If issues arise, the old `db.py` module remains unchanged. You can:

1. Revert import changes
2. The repository pattern is additive, not destructive
3. Both patterns can coexist during migration

## Best Practices

1. **Initialize once**: Create repository instances at module level
2. **Don't catch all exceptions**: Let repositories handle DynamoDB errors
3. **Use return values**: Check boolean returns for operation success
4. **Trust the logging**: Repositories log all operations and errors
5. **Leverage type hints**: IDEs will help with correct usage

## Future Enhancements

The repository pattern enables future improvements:

1. **Caching**: Add Redis caching layer transparently
2. **Metrics**: Add CloudWatch metrics for all operations
3. **Batch operations**: Implement batch gets/writes
4. **Transactions**: Add DynamoDB transaction support
5. **Event sourcing**: Emit events for all state changes

## Support

For questions or issues during migration:

1. Check the repository source code for implementation details
2. Review test files for usage examples
3. Check logs for detailed error information
4. The repositories are designed to be self-documenting with type hints