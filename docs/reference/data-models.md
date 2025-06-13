# Data Models

*Last Updated: December 2024*

## Overview

CivicForge uses a single-table design pattern in DynamoDB for optimal performance and cost efficiency. This document details all data models, their relationships, and access patterns.

## Table of Contents

1. [Database Design](#database-design)
2. [Core Models](#core-models)
3. [Access Patterns](#access-patterns)
4. [Indexes](#indexes)
5. [Data Validation](#data-validation)
6. [Migration Strategy](#migration-strategy)

## Database Design

### Single Table Design

All data is stored in one DynamoDB table with the following structure:

```
Table Name: civicforge-{stage}
Primary Key: PK (Partition Key)
Sort Key: SK (Sort Key)
```

### Key Design Patterns

| Entity | PK | SK |
|--------|----|----|
| User | USER#{userId} | USER#{userId} |
| Quest | QUEST#{questId} | QUEST#{questId} |
| User's Created Quests | USER#{userId} | QUEST#CREATED#{timestamp} |
| User's Performed Quests | USER#{userId} | QUEST#PERFORMED#{timestamp} |
| Failed Reward | REWARD#FAILED | QUEST#{questId}#USER#{userId}#{timestamp} |

## Core Models

### User

Represents a registered user in the system.

```python
class User(BaseModel):
    userId: str                    # UUID, matches Cognito sub
    username: str                  # Unique username
    email: str                     # Email address
    emailVerified: bool           # Email verification status
    createdAt: datetime           # Account creation timestamp
    updatedAt: datetime           # Last update timestamp
    
    # Reputation metrics
    reputation: int = 0           # Total reputation score
    experiencePoints: int = 0     # Total XP earned
    
    # Statistics
    questsCreated: int = 0        # Number of quests created
    questsCompleted: int = 0      # Number of quests completed
    attestationsGiven: int = 0    # Number of attestations given
    attestationsReceived: int = 0 # Number of attestations received
    
    # Profile
    bio: Optional[str] = None     # User biography
    avatarUrl: Optional[str] = None # Profile picture URL
    wallet: Optional[str] = None  # Ethereum wallet address
```

### Quest

Represents a task or challenge created by a user.

```python
class Quest(BaseModel):
    questId: str                  # UUID
    creatorId: str                # User ID of creator
    title: str                    # Quest title (3-100 chars)
    description: str              # Detailed description (10-1000 chars)
    
    # Rewards
    rewardXp: int                 # Experience points (min: 10)
    rewardReputation: int         # Reputation points (min: 1)
    
    # Status tracking
    status: QuestStatus           # OPEN, CLAIMED, PENDING_REVIEW, COMPLETE, DISPUTED
    performerId: Optional[str]    # User ID of performer
    
    # Timestamps
    createdAt: datetime           # Creation timestamp
    claimedAt: Optional[datetime] # Claim timestamp
    submittedAt: Optional[datetime] # Submission timestamp
    completedAt: Optional[datetime] # Completion timestamp
    updatedAt: datetime           # Last update timestamp
    
    # Content
    submission: Optional[str]     # Performer's submission text
    attestations: List[Attestation] = [] # List of attestations
    
    # Metadata
    tags: List[str] = []         # Quest tags/categories
    requirements: List[str] = [] # Specific requirements
    expiresAt: Optional[datetime] # Optional expiration
```

### QuestStatus Enum

```python
class QuestStatus(str, Enum):
    OPEN = "OPEN"                    # Available to claim
    CLAIMED = "CLAIMED"              # Claimed by performer
    PENDING_REVIEW = "PENDING_REVIEW" # Submitted, awaiting attestation
    COMPLETE = "COMPLETE"            # Attested and rewards distributed
    DISPUTED = "DISPUTED"            # Under dispute
    EXPIRED = "EXPIRED"              # Past expiration date
    CANCELLED = "CANCELLED"          # Cancelled by creator
```

### Attestation

Represents verification of quest completion.

```python
class Attestation(BaseModel):
    attesterId: str              # User ID of attester
    attesterUsername: str        # Username for display
    rating: int                  # Rating 1-5
    comments: Optional[str]      # Attestation comments
    timestamp: datetime          # When attested
    signature: Optional[str]     # EIP-712 signature (future)
    
    # Metadata
    onChain: bool = False       # Whether recorded on blockchain
    transactionHash: Optional[str] # Blockchain transaction hash
```

### FailedReward

Tracks failed reward distributions for retry processing.

```python
class FailedReward(BaseModel):
    questId: str                # Quest ID
    userId: str                 # User ID who should receive reward
    rewardType: str             # "XP" or "REPUTATION"
    rewardAmount: int           # Amount to distribute
    reason: str                 # Failure reason
    attemptCount: int = 1       # Number of attempts
    createdAt: datetime         # First failure timestamp
    lastAttemptAt: datetime     # Last attempt timestamp
    status: str                 # "PENDING", "PROCESSING", "COMPLETED", "FAILED"
    
    # Processing metadata
    errorDetails: Optional[dict] # Detailed error information
    processedAt: Optional[datetime] # When successfully processed
    processedBy: Optional[str]   # Lambda request ID that processed
```

## Access Patterns

### Primary Access Patterns

1. **Get User by ID**
   ```
   PK: USER#{userId}
   SK: USER#{userId}
   ```

2. **Get Quest by ID**
   ```
   PK: QUEST#{questId}
   SK: QUEST#{questId}
   ```

3. **List User's Created Quests**
   ```
   PK: USER#{userId}
   SK: begins_with("QUEST#CREATED#")
   ```

4. **List User's Performed Quests**
   ```
   PK: USER#{userId}
   SK: begins_with("QUEST#PERFORMED#")
   ```

5. **List Failed Rewards**
   ```
   PK: REWARD#FAILED
   SK: begins_with("QUEST#")
   ```

### Secondary Access Patterns (via GSI)

1. **List All Open Quests**
   ```
   GSI: StatusIndex
   GSI_PK: STATUS#OPEN
   GSI_SK: CREATED#{timestamp}
   ```

2. **List Quests by Creator**
   ```
   GSI: CreatorIndex
   GSI_PK: CREATOR#{userId}
   GSI_SK: CREATED#{timestamp}
   ```

## Indexes

### Global Secondary Indexes (GSIs)

#### StatusIndex
- **Purpose**: Query quests by status
- **Partition Key**: GSI1_PK (STATUS#{status})
- **Sort Key**: GSI1_SK (CREATED#{timestamp})
- **Attributes**: All quest attributes

#### CreatorIndex
- **Purpose**: Query quests by creator
- **Partition Key**: GSI2_PK (CREATOR#{userId})
- **Sort Key**: GSI2_SK (CREATED#{timestamp})
- **Attributes**: All quest attributes

#### PerformerIndex
- **Purpose**: Query quests by performer
- **Partition Key**: GSI3_PK (PERFORMER#{userId})
- **Sort Key**: GSI3_SK (UPDATED#{timestamp})
- **Attributes**: All quest attributes

## Data Validation

### Pydantic Models

All data is validated using Pydantic before database operations:

```python
class CreateQuestRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=1000)
    rewardXp: int = Field(..., ge=10, le=10000)
    rewardReputation: int = Field(..., ge=1, le=100)
    
    @validator('title')
    def validate_title(cls, v):
        # Remove dangerous characters
        return sanitize_input(v)
```

### Database Constraints

Using DynamoDB conditional expressions:

```python
# Prevent duplicate claims
condition_expression = Attr('status').eq('OPEN') & 
                      Attr('performerId').not_exists()

# Prevent concurrent updates
condition_expression = Attr('version').eq(current_version)
```

## Migration Strategy

### Schema Evolution

1. **Backward Compatible Changes**
   - Add optional fields with defaults
   - Use feature flags for gradual rollout

2. **Breaking Changes**
   - Create new models with version suffix
   - Run dual writes during migration
   - Backfill historical data
   - Switch reads to new model
   - Clean up old data

### Migration Example

```python
# v1 Model
class UserV1:
    userId: str
    username: str
    reputation: int

# v2 Model (adds experiencePoints)
class UserV2:
    userId: str
    username: str
    reputation: int
    experiencePoints: int = 0  # Default for existing users

# Migration function
def migrate_user_v1_to_v2(user_v1):
    return UserV2(
        **user_v1.dict(),
        experiencePoints=calculate_xp_from_history(user_v1.userId)
    )
```

## Best Practices

### Key Design
- Use hierarchical keys for related data
- Include entity type in keys
- Use sortable timestamps (ISO 8601)

### Data Modeling
- Denormalize for read performance
- Use composite keys for relationships
- Minimize hot partitions

### Consistency
- Use conditional updates
- Implement optimistic locking
- Handle eventual consistency

### Cost Optimization
- Project only needed attributes
- Use batch operations
- Implement efficient pagination

## Future Enhancements

### Planned Features

1. **Quest Categories**
   ```python
   class Category(BaseModel):
       categoryId: str
       name: str
       description: str
       questCount: int
   ```

2. **Team Quests**
   ```python
   class TeamQuest(Quest):
       maxPerformers: int
       performers: List[str]
       individualRewards: bool
   ```

3. **Quest Templates**
   ```python
   class QuestTemplate(BaseModel):
       templateId: str
       title: str
       description: str
       defaultRewards: dict
   ```

### Blockchain Integration

Future support for on-chain attestations:

```python
class OnChainAttestation(Attestation):
    blockNumber: int
    transactionHash: str
    contractAddress: str
    tokenId: Optional[int]  # For NFT attestations
```