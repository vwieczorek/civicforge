# ADR-003: IAM Least Privilege Implementation

- **Status:** Accepted
- **Date:** 2025-01-17
- **Context:** Initial IAM policies were overly permissive, including wildcard account IDs and broad DynamoDB permissions.

## Decision

Implement strict least-privilege IAM policies with attribute-level restrictions for DynamoDB operations.

### Key Implementations:
1. Replace wildcard account IDs with `${aws:accountId}`
2. Restrict DynamoDB UpdateItem to specific attributes
3. Separate read and write permissions
4. Function-specific IAM roles

### Example:
```yaml
Condition:
  ForAllValues:StringEquals:
    "dynamodb:Attributes":
      - "xp"
      - "reputation"
      - "updatedAt"
```

## Consequences

### Positive:
- **Security**: Minimizes blast radius of compromised functions
- **Compliance**: Meets security audit requirements
- **Audit Trail**: Clear permissions for each function
- **Defense in Depth**: Multiple layers of security

### Negative:
- **Complexity**: More complex IAM policies to maintain
- **Development Friction**: Developers need to update policies for new attributes
- **Debugging**: Permission errors can be harder to diagnose
- **Verbosity**: Longer, more detailed configuration files

### Trade-offs:
- Chose security over developer convenience
- Chose explicit configuration over implicit permissions
- Chose attribute-level control over table-level access

## Lessons Learned

1. Start with least privilege from day one
2. Use tools like IAM Policy Simulator during development
3. Document why each permission is needed
4. Regular security audits catch overly broad permissions