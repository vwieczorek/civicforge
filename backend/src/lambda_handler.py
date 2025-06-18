"""
Lambda handler utilities for structured logging and observability
"""

from typing import Callable, Any, Dict
from functools import wraps
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from .logger import logger, metrics, tracer
import time
import json


def lambda_handler(handler_func: Callable) -> Callable:
    """
    Decorator for Lambda handlers that adds structured logging,
    metrics, and tracing capabilities
    """
    @wraps(handler_func)
    @logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
    @tracer.capture_lambda_handler
    @metrics.log_metrics
    def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        # Log incoming request
        logger.info("Lambda invocation started", extra={
            "request_id": context.request_id,
            "function_name": context.function_name,
            "remaining_time_ms": context.get_remaining_time_in_millis()
        })
        
        # Add custom metric for invocation
        metrics.add_metric(name="LambdaInvocation", unit=MetricUnit.Count, value=1)
        
        start_time = time.time()
        
        try:
            # Call the actual handler
            response = handler_func(event, context)
            
            # Log successful completion
            duration_ms = (time.time() - start_time) * 1000
            logger.info("Lambda invocation completed", extra={
                "duration_ms": duration_ms,
                "status_code": response.get("statusCode", 200)
            })
            
            # Add success metric
            metrics.add_metric(name="SuccessfulInvocation", unit=MetricUnit.Count, value=1)
            metrics.add_metric(name="InvocationDuration", unit=MetricUnit.Milliseconds, value=duration_ms)
            
            return response
            
        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            logger.exception("Lambda invocation failed", extra={
                "duration_ms": duration_ms,
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            
            # Add error metric
            metrics.add_metric(name="FailedInvocation", unit=MetricUnit.Count, value=1)
            metrics.add_metric(name="ErrorDuration", unit=MetricUnit.Milliseconds, value=duration_ms)
            
            # Re-raise the exception
            raise
    
    return wrapper


def log_api_request(method: str, path: str, status_code: int, duration_ms: float):
    """
    Log API request with structured data
    """
    logger.info("API request processed", extra={
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms
    })
    
    # Add metrics
    metrics.add_metric(name="APIRequest", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="APIRequestDuration", unit=MetricUnit.Milliseconds, value=duration_ms)
    
    # Add dimension for status code
    metrics.add_metadata(key="StatusCode", value=str(status_code))
    metrics.add_metadata(key="Method", value=method)
    metrics.add_metadata(key="Path", value=path)