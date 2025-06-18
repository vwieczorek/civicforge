"""Security metrics utility for CloudWatch monitoring."""
import os
from typing import Optional, Dict, Any
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit
import structlog

logger = structlog.get_logger()

# Initialize metrics with custom namespace
metrics = Metrics(namespace=f"{os.environ.get('SERVICE_NAME', 'civicforge')}/{os.environ.get('STAGE', 'dev')}")


def record_authentication_failure(user_id: Optional[str] = None, reason: str = "unknown"):
    """Record authentication failure for monitoring."""
    metrics.add_metric(name="AuthenticationFailures", unit=MetricUnit.Count, value=1)
    metrics.add_metadata("reason", reason)
    if user_id:
        metrics.add_metadata("user_id", user_id)
    
    logger.warning(
        "authentication_failure",
        user_id=user_id,
        reason=reason
    )


def record_rate_limit_exceeded(user_id: Optional[str] = None, endpoint: Optional[str] = None):
    """Record rate limit exceeded event."""
    metrics.add_metric(name="RateLimitExceeded", unit=MetricUnit.Count, value=1)
    if user_id:
        metrics.add_metadata("user_id", user_id)
    if endpoint:
        metrics.add_metadata("endpoint", endpoint)
    
    logger.warning(
        "rate_limit_exceeded",
        user_id=user_id,
        endpoint=endpoint
    )


def record_invalid_token_attempt(token_type: str = "unknown", error: Optional[str] = None):
    """Record invalid token attempt."""
    metrics.add_metric(name="InvalidTokenAttempts", unit=MetricUnit.Count, value=1)
    metrics.add_metadata("token_type", token_type)
    if error:
        metrics.add_metadata("error", error)
    
    logger.warning(
        "invalid_token_attempt",
        token_type=token_type,
        error=error
    )


def record_suspicious_activity(activity_type: str, details: Dict[str, Any]):
    """Record suspicious activity for security monitoring."""
    metrics.add_metric(name="SuspiciousActivity", unit=MetricUnit.Count, value=1)
    metrics.add_metadata("activity_type", activity_type)
    for key, value in details.items():
        metrics.add_metadata(key, str(value))
    
    logger.warning(
        "suspicious_activity",
        activity_type=activity_type,
        **details
    )


def record_security_event(event_type: str, severity: str, details: Dict[str, Any]):
    """Record general security event."""
    metrics.add_metric(name=f"SecurityEvent_{severity}", unit=MetricUnit.Count, value=1)
    metrics.add_metadata("event_type", event_type)
    metrics.add_metadata("severity", severity)
    for key, value in details.items():
        metrics.add_metadata(key, str(value))
    
    log_func = logger.error if severity == "critical" else logger.warning
    log_func(
        "security_event",
        event_type=event_type,
        severity=severity,
        **details
    )