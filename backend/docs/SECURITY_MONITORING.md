# Security Monitoring Guide

This guide explains the security monitoring features implemented in CivicForge and how to use them effectively.

## Overview

CivicForge implements comprehensive security monitoring using:
- CloudWatch Alarms for real-time alerting
- Structured security metrics for tracking
- Automated responses to security events

## Security Metrics

### Authentication Failures
- **Metric**: `AuthenticationFailures`
- **Namespace**: `civicforge/{stage}`
- **Triggered by**: Failed JWT validation, unexpected errors during auth
- **Alarm Threshold**: 10 failures in 5 minutes

### Rate Limit Violations
- **Metric**: `RateLimitExceeded`
- **Namespace**: `civicforge/{stage}`
- **Triggered by**: When API rate limits are exceeded
- **Alarm Threshold**: 50 violations in 5 minutes

### Invalid Token Attempts
- **Metric**: `InvalidTokenAttempts`
- **Namespace**: `civicforge/{stage}`
- **Triggered by**: Expired tokens, invalid JWT signatures, wrong token_use
- **Alarm Threshold**: 20 attempts in 5 minutes

### DynamoDB Throttling
- **Metrics**: 
  - `ConsumedReadCapacityUnits` for Quests table
  - `ConsumedReadCapacityUnits` for Users table
- **Namespace**: `AWS/DynamoDB`
- **Alarm Threshold**: 80% of provisioned capacity

### API Gateway Errors
- **Metric**: `4XXError`
- **Namespace**: `AWS/ApiGateway`
- **Alarm Threshold**: 100 errors in 10 minutes (2 evaluation periods)

## CloudWatch Alarms

All alarms are automatically created by the serverless framework:

```yaml
# Example alarm configuration
AuthenticationFailuresAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: ${self:service}-${self:provider.stage}-auth-failures
    MetricName: AuthenticationFailures
    Namespace: ${self:service}/${self:provider.stage}
    Threshold: 10
```

## Emitting Security Metrics

### From Lambda Functions

Use the security metrics utility:

```python
from src.utils.security_metrics import (
    record_authentication_failure,
    record_rate_limit_exceeded,
    record_invalid_token_attempt,
    record_suspicious_activity
)

# Record auth failure
record_authentication_failure(user_id="user123", reason="invalid_credentials")

# Record rate limit
record_rate_limit_exceeded(user_id="user123", endpoint="/api/quests")

# Record invalid token
record_invalid_token_attempt(token_type="jwt", error="expired")

# Record suspicious activity
record_suspicious_activity(
    activity_type="multiple_failed_logins",
    details={"user_id": "user123", "attempts": 5}
)
```

### Automatic Recording

Security metrics are automatically recorded in:
- `auth.py` - JWT validation failures
- `rate_limiter.py` - Rate limit violations

## Viewing Metrics

### CloudWatch Console

1. Navigate to CloudWatch → Metrics
2. Select namespace: `civicforge/{stage}`
3. View metric dimensions and graphs

### CloudWatch Logs Insights

Query security events:

```sql
fields @timestamp, @message
| filter @message like /security_event/
| sort @timestamp desc
| limit 100
```

Find authentication failures:

```sql
fields @timestamp, user_id, reason
| filter @message like /authentication_failure/
| stats count() by reason
```

## Responding to Alarms

### Immediate Actions

1. **Authentication Failures Spike**
   - Check for credential stuffing attacks
   - Review failed auth logs for patterns
   - Consider temporarily blocking suspicious IPs

2. **Rate Limit Violations**
   - Identify the source (user or IP)
   - Check if legitimate usage spike
   - Consider adjusting limits if needed

3. **Invalid Token Attempts**
   - Could indicate token replay attacks
   - Check token expiry settings
   - Review JWKS rotation

4. **DynamoDB Throttling**
   - Scale up provisioned capacity
   - Review access patterns
   - Enable auto-scaling if not already

### Investigation Steps

1. **Check CloudWatch Logs**
   ```bash
   aws logs tail /aws/lambda/civicforge-{stage}-api --follow
   ```

2. **Query Metrics**
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace civicforge/{stage} \
     --metric-name AuthenticationFailures \
     --start-time 2024-01-01T00:00:00Z \
     --end-time 2024-01-01T01:00:00Z \
     --period 300 \
     --statistics Sum
   ```

3. **Review X-Ray Traces**
   - Look for unusual patterns
   - Check service map for bottlenecks

## Security Event Types

### Critical Events
- Multiple authentication failures from same IP
- Sudden spike in 4XX errors
- DynamoDB capacity exceeded

### Warning Events
- Individual auth failures
- Rate limit hits
- Invalid token attempts

### Info Events
- Successful authentications
- Normal API usage patterns

## Best Practices

1. **Set Up SNS Notifications**
   - Add SNS topic to alarms
   - Configure email/SMS alerts
   - Integrate with PagerDuty/Slack

2. **Regular Review**
   - Weekly review of security metrics
   - Monthly analysis of trends
   - Quarterly threshold adjustments

3. **Automation**
   - Auto-scale DynamoDB tables
   - Automated IP blocking for attacks
   - Lambda concurrency reservations

4. **Documentation**
   - Document all security incidents
   - Track false positives
   - Update thresholds based on patterns

## Testing Security Monitoring

### Trigger Test Alarms

1. **Test Auth Failures**
   ```bash
   # Send invalid tokens
   for i in {1..15}; do
     curl -H "Authorization: Bearer invalid" \
       https://api.civicforge.com/users/me
   done
   ```

2. **Test Rate Limits**
   ```bash
   # Exceed rate limit
   for i in {1..60}; do
     curl https://api.civicforge.com/quests
   done
   ```

### Verify Metrics

Check CloudWatch to ensure metrics appear:
- Metrics should appear within 1-2 minutes
- Alarms should trigger at thresholds
- Logs should contain security events

## Integration with SIEM

For enterprise deployments, export metrics to SIEM:

1. **CloudWatch Logs → Kinesis Data Firehose**
2. **Kinesis → S3 → SIEM ingestion**
3. **Real-time streaming to Splunk/ELK**

## Compliance

Security monitoring helps with:
- SOC 2 compliance (logging requirements)
- GDPR (security breach detection)
- PCI DSS (if processing payments)

Keep logs for:
- Authentication events: 90 days minimum
- Security incidents: 1 year
- Normal API logs: 30 days

## Future Enhancements

1. **Machine Learning**
   - Anomaly detection for user behavior
   - Predictive threat analysis
   - Automated response workflows

2. **Advanced Metrics**
   - Geo-location based monitoring
   - Device fingerprinting
   - Session analysis

3. **Integration**
   - AWS Security Hub
   - GuardDuty findings
   - WAF rule updates