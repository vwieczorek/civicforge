# DynamoDB Data Access Patterns

This document provides a comprehensive overview of all DynamoDB access patterns used in the CivicForge backend. It serves as a reference for developers and is essential for implementing the repository pattern.

## Table of Contents
1. [Tables and Configuration](#tables-and-configuration)
2. [User Entity Access Patterns](#user-entity-access-patterns)
3. [Quest Entity Access Patterns](#quest-entity-access-patterns)
4. [Failed Rewards Entity Access Patterns](#failed-rewards-entity-access-patterns)
5. [Global Secondary Indexes](#global-secondary-indexes)
6. [Atomic Operations and Patterns](#atomic-operations-and-patterns)
7. [Best Practices](#best-practices)

## Tables and Configuration

### Table Names
- **Users Table**: `USERS_TABLE` (environment variable, default: "civicforge-users")
- **Quests Table**: `QUESTS_TABLE` (environment variable, default: "civicforge-quests")
- **Failed Rewards Table**: `FAILED_REWARDS_TABLE` (environment variable)

### Key Schema
- **Users Table**: 
  - Partition Key: `userId` (String)
- **Quests Table**: 
  - Partition Key: `questId` (String)
- **Failed Rewards Table**: 
  - Partition Key: `recordId` (String)

## User Entity Access Patterns

### 1. Get User by ID
**Location**: `db.py:67-83`
```python
Operation: get_item
Key: {"userId": user_id}
Use Case: Retrieve user profile, check permissions
```

### 2. Create User
**Location**: `db.py:101-115`, `triggers/create_user.py:71-74`
```python
Operation: put_item
Condition: attribute_not_exists(userId)  # Idempotency
Fields: {
    userId, username, reputation: 0, experience: 0, 
    questCreationPoints: INITIAL_POINTS, 
    createdAt, updatedAt
}
```

### 3. Award Rewards (Atomic)
**Location**: `db.py:177-202`
```python
Operation: update_item
UpdateExpression: "ADD experience :xp, reputation :rep SET updatedAt = :now"
Purpose: Atomically increment XP and reputation
```

### 4. Deduct Quest Creation Points (Conditional)
**Location**: `db.py:204-223`
```python
Operation: update_item
UpdateExpression: "SET questCreationPoints = questCreationPoints - :points, updatedAt = :now"
ConditionExpression: "questCreationPoints >= :points"
Purpose: Prevent negative balance
```

### 5. Update Wallet Address
**Location**: `db.py:551-566`
```python
Operation: update_item
UpdateExpression: "SET walletAddress = :addr, updatedAt = :now"
```

### 6. Award Quest Points (Refund)
**Location**: `db.py:568-584`
```python
Operation: update_item
UpdateExpression: "ADD questCreationPoints :points SET updatedAt = :now"
```

### 7. Idempotent Reward Processing
**Location**: `triggers/reprocess_failed_rewards.py:215-271`
```python
Operation: update_item
UpdateExpression: Dynamic based on rewards + "ADD processedRewardIds :reward_id_set"
ConditionExpression: "NOT contains(processedRewardIds, :reward_id_str)"
Purpose: Ensure rewards are only processed once
```

## Quest Entity Access Patterns

### 1. Get Quest by ID
**Location**: `db.py:85-99`
```python
Operation: get_item
Key: {"questId": quest_id}
```

### 2. Get Quest for Update (Strong Consistency)
**Location**: `db.py:160-175`
```python
Operation: get_item
Key: {"questId": quest_id}
ConsistentRead: True
Purpose: Ensure latest data before state changes
```

### 3. Create Quest
**Location**: `db.py:144-158`
```python
Operation: put_item
Fields: All quest fields including timestamps
```

### 4. Update Quest (Full Replacement)
**Location**: `db.py:117-142`
```python
Operation: put_item
Purpose: Replace entire quest document
```

### 5. Claim Quest (Atomic)
**Location**: `db.py:631-655`
```python
Operation: update_item
UpdateExpression: "SET performerId = :pid, #s = :claimed_status, claimedAt = :now"
ConditionExpression: "#s = :open_status AND (attribute_not_exists(performerId) OR performerId = :null)"
Purpose: Prevent double claiming
```

### 6. Submit Quest (Atomic)
**Location**: `db.py:657-681`
```python
Operation: update_item
UpdateExpression: "SET #s = :submitted_status, submittedAt = :now, submissionText = :st"
ConditionExpression: "#s = :claimed_status AND performerId = :pid"
Purpose: Ensure only performer can submit
```

### 7. Add Attestation (Atomic)
**Location**: `db.py:586-629`
```python
Operation: update_item
UpdateExpression: "SET attestations = list_append(...), {condition_field} = :true, ADD attesterIds :user_id_set"
ConditionExpression: "#status = :submitted_status AND NOT contains(attesterIds, :user_id)"
Purpose: Prevent duplicate attestations, track unique attesters
```

### 8. Complete Quest (Atomic)
**Location**: `db.py:683-704`
```python
Operation: update_item
UpdateExpression: "SET #S = :complete_status, completedAt = :now"
ConditionExpression: "#S = :submitted_status AND hasRequestorAttestation = :true AND hasPerformerAttestation = :true"
Purpose: Ensure both attestations exist before completion
```

### 9. Dispute Quest (Atomic)
**Location**: `db.py:728-751`
```python
Operation: update_item
UpdateExpression: "SET #S = :disputed_status, disputeReason = :reason, updatedAt = :now"
ConditionExpression: "#S = :submitted_status AND (creatorId = :uid OR performerId = :uid)"
Purpose: Only involved parties can dispute
```

### 10. Delete Quest (Conditional)
**Location**: `db.py:706-726`
```python
Operation: delete_item
ConditionExpression: "creatorId = :uid AND #s = :open_status"
Purpose: Only creator can delete, only if OPEN
```

### 11. List Quests by Status
**Location**: `db.py:318-370`
```python
Primary: query on GSI "StatusIndex"
Fallback: scan with FilterExpression
Pagination: LastEvaluatedKey
Sort: By createdAt descending
```

### 12. Get User Created Quests
**Location**: `db.py:407-454`
```python
Primary: query on GSI "CreatorIndex"
KeyCondition: "creatorId = :uid"
Fallback: scan with FilterExpression
Pagination: ExclusiveStartKey, Limit
Sort: ScanIndexForward = False (newest first)
```

### 13. Get User Performed Quests
**Location**: `db.py:456-503`
```python
Primary: query on GSI "PerformerIndex"
KeyCondition: "performerId = :uid"
Fallback: scan with FilterExpression
Pagination: ExclusiveStartKey, Limit
```

## Failed Rewards Entity Access Patterns

### 1. Track Failed Reward
**Location**: `db.py:281-316`
```python
Operation: put_item
Fields: {
    recordId, userId, questId, xp, reputation, 
    error, status: 'pending', createdAt, retryCount: 0
}
```

### 2. Get Pending Failed Rewards
**Location**: `db.py:225-259`
```python
Operation: query on GSI "status-createdAt-index"
KeyCondition: "#s = :status" (status = 'pending')
Pagination: LastEvaluatedKey
```

### 3. Mark Reward Completed
**Location**: `db.py:261-279`
```python
Operation: update_item
UpdateExpression: "SET #s = :status, completedAt = :now"
Purpose: Set status to 'completed'
```

### 4. Acquire Processing Lease (Distributed Lock)
**Location**: `triggers/reprocess_failed_rewards.py:105-133`
```python
Operation: update_item
UpdateExpression: "SET leaseOwner = :owner, leaseExpiresAt = :expiry"
ConditionExpression: Lease not exists or expired
Purpose: Implement distributed locking pattern
```

### 5. Update Reward Status
**Location**: `triggers/reprocess_failed_rewards.py:273-296`
```python
Operation: update_item
UpdateExpression: Dynamic based on status
Purpose: Track retry count and timestamps
```

## Global Secondary Indexes

### 1. StatusIndex (Quests Table)
- **Partition Key**: `status`
- **Use Case**: Query quests by status
- **Access Pattern**: List all quests with a specific status

### 2. CreatorIndex (Quests Table)
- **Partition Key**: `creatorId`
- **Use Case**: Query quests created by a user
- **Access Pattern**: Get all quests created by a specific user

### 3. PerformerIndex (Quests Table)
- **Partition Key**: `performerId`
- **Use Case**: Query quests performed by a user
- **Access Pattern**: Get all quests claimed/performed by a specific user

### 4. status-createdAt-index (Failed Rewards Table)
- **Partition Key**: `status`
- **Sort Key**: `createdAt`
- **Use Case**: Query pending rewards in chronological order
- **Access Pattern**: Process failed rewards in FIFO order

## Atomic Operations and Patterns

### 1. Idempotency Patterns
- **User Creation**: Uses `attribute_not_exists(userId)`
- **Reward Processing**: Uses Set data type with `NOT contains()` check
- **Attestations**: Uses Set data type to track unique attesters

### 2. State Machine Enforcement
All quest state transitions use conditional expressions:
- OPEN → CLAIMED: Check status is OPEN
- CLAIMED → SUBMITTED: Check status is CLAIMED and performer matches
- SUBMITTED → COMPLETED: Check both attestations exist
- SUBMITTED → DISPUTED: Check user is involved party

### 3. Concurrency Control
- **Optimistic Locking**: Via conditional expressions
- **Distributed Locking**: Lease pattern for failed reward processing
- **Atomic Counters**: ADD operation for numeric fields

### 4. Data Integrity
- **Balance Checks**: Quest point deduction with minimum balance
- **Double-Submit Prevention**: Attestation uniqueness via Sets
- **Race Condition Prevention**: All critical operations use conditions

## Best Practices

### 1. Consistency Requirements
- Use `ConsistentRead: True` before critical updates
- Default to eventual consistency for read-heavy operations

### 2. Pagination Strategy
- **Token-based**: For API endpoints (base64 encoded LastEvaluatedKey)
- **Limit enforcement**: Default 20, max 100 items
- **Separate tokens**: For multiple result sets (created/performed quests)

### 3. Error Handling
- Retry with exponential backoff for throttling
- Handle conditional check failures gracefully
- Log all DynamoDB errors for monitoring

### 4. Performance Optimization
- Always use GSIs instead of scans when possible
- Batch operations where applicable
- Project only required attributes in queries

### 5. Data Types
- **String Set (SS)**: For unique collections (attesterIds)
- **List (L)**: For ordered collections (attestations)
- **Number (N)**: For all numeric values
- **Boolean (BOOL)**: For flags
- **NULL**: For optional fields and clearing values

### 6. Security Considerations
- Never expose internal IDs in error messages
- Validate all input before DynamoDB operations
- Use IAM conditions to restrict attribute updates

## Repository Pattern Implementation Guide

When implementing the repository pattern based on these access patterns:

1. **Create separate repositories** for each entity (UserRepository, QuestRepository, FailedRewardRepository)

2. **Encapsulate complexity**: Hide DynamoDB-specific details behind clean interfaces

3. **Enforce patterns**: Ensure all operations follow the documented patterns

4. **Add validation**: Validate business rules before database operations

5. **Implement retries**: Add automatic retry logic with backoff

6. **Use typing**: Leverage Python type hints for all methods

7. **Test thoroughly**: Mock DynamoDB responses for unit tests

Example structure:
```python
class QuestRepository:
    async def get_by_id(self, quest_id: str) -> Optional[Quest]:
        # Implements pattern from db.py:85-99
        
    async def claim_quest(self, quest_id: str, performer_id: str) -> Quest:
        # Implements atomic claim pattern from db.py:631-655
        # Handles ConditionalCheckFailedException
```

This documentation should be updated whenever new access patterns are added or existing ones are modified.