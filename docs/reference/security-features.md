# Security Features

## Overview

CivicForge implements multiple layers of security to ensure data integrity, prevent unauthorized access, and protect against common attack vectors.

## Key Security Features

### 1. Least-Privilege IAM Permissions

Each Lambda function has narrowly scoped IAM permissions:

- **api**: Read-only access to DynamoDB tables (explicitly denied DeleteItem)
- **createQuest**: Can only PutItem to quests table and UpdateItem on users table
- **attestQuest**: Can only UpdateItem on quests table and specific user attributes (reputation, experience, questCreationPoints, processedRewardIds)
- **deleteQuest**: Can only DeleteItem with ownership verification
- **updateWallet**: Isolated handler that can only update walletAddress field

### 2. EIP-712 Nonce System

Implemented to prevent replay attacks in attestation signatures:

```typescript
// Nonce generation and storage
const nonce = crypto.randomBytes(32).toString('hex');
await dynamodb.updateItem({
  TableName: process.env.USERS_TABLE_NAME,
  Key: { userId },
  UpdateExpression: 'SET #n = :nonce, #exp = :expiry',
  ExpressionAttributeNames: {
    '#n': 'currentNonce',
    '#exp': 'nonceExpiry'
  },
  ExpressionAttributeValues: {
    ':nonce': nonce,
    ':expiry': Date.now() + 300000 // 5 minutes
  }
});
```

### 3. Granular DynamoDB Conditions

DynamoDB operations use condition expressions to ensure data integrity:

```javascript
// Example: Only allow quest deletion by owner
ConditionExpression: 'creatorId = :userId',
ExpressionAttributeValues: {
  ':userId': userId
}
```

### 4. Request Validation

All API endpoints validate request data:
- Required fields presence
- Data type validation
- Business logic validation (e.g., reward minimums)

### 5. AWS Cognito Authentication

- JWT token validation on all protected endpoints
- User pool with password policies
- MFA capability (optional)

## Security Best Practices

1. **Never log sensitive data**: No PII or authentication tokens in logs
2. **Use parameterized queries**: All DynamoDB operations use parameterized inputs
3. **Validate all inputs**: Both client and server-side validation
4. **Principle of least privilege**: Each component has minimum required permissions
5. **Defense in depth**: Multiple layers of security controls

## Incident Response

In case of security incidents:

1. Check CloudWatch logs for suspicious activity
2. Review IAM permissions for any changes
3. Verify DynamoDB conditional checks are enforced
4. Check for any unauthorized API calls in CloudTrail

### 6. Wallet Update Isolation

Wallet address updates are handled by a separate Lambda function with:
- Dedicated endpoint `/api/v1/users/wallet`
- IAM permissions restricted to only update `walletAddress` and `updatedAt` fields
- Cannot modify any other user attributes
- Requires authentication (future: password re-authentication)

### 7. Attestation Deduplication

The attestation system prevents duplicate attestations:
- Uses DynamoDB SET to track `attesterIds`
- Atomic condition checks prevent race conditions
- Each user can only attest once per quest

## Future Enhancements

- [ ] Implement rate limiting per user
- [ ] Add WAF rules for common attack patterns
- [ ] Enable AWS GuardDuty for threat detection
- [ ] Implement API key rotation schedule
- [ ] Add time-lock for wallet updates
- [ ] Password re-authentication for sensitive operations