# ADR-002: Lambda Function Separation Strategy

- **Status:** Accepted
- **Date:** 2025-01-15
- **Context:** Need to balance between monolithic and microservice approaches for Lambda functions while maintaining security and operational clarity.

## Decision

We separated critical operations into dedicated Lambda functions while keeping read-heavy operations in a general API handler.

### Function Separation:
1. **API Handler**: General reads and non-critical updates
2. **CreateQuest**: Isolated due to point deduction logic
3. **AttestQuest**: Isolated due to reward distribution
4. **DeleteQuest**: Isolated due to deletion sensitivity
5. **Triggers**: Separate functions for async operations

## Consequences

### Positive:
- **Security**: Fine-grained IAM policies per function
- **Observability**: Clear metrics and logs per operation
- **Scaling**: Functions scale independently
- **Failure Isolation**: Issues don't affect other operations
- **Development**: Teams can work on functions independently

### Negative:
- **Complexity**: More functions to manage and deploy
- **Cold Starts**: More potential cold start scenarios
- **Code Duplication**: Some shared logic needs copying
- **Deployment**: More complex deployment process

### Trade-offs:
- Chose security over simplicity
- Chose operational clarity over development speed
- Chose fine-grained control over monolithic simplicity

## Alternatives Considered

1. **Single Monolith**: All logic in one Lambda
   - Rejected due to security and scaling concerns
2. **Full Microservices**: One function per endpoint
   - Rejected as overkill for current scale
3. **Domain Separation**: Functions by business domain
   - Partially adopted, may fully adopt in future