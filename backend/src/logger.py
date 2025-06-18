"""
Centralized logging configuration using AWS Lambda Powertools
"""

from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.tracing import Tracer
import os

# Initialize logger with service name from environment or default
service_name = os.getenv("SERVICE_NAME", "civicforge")
stage = os.getenv("STAGE", "dev")

# Create logger instance
logger = Logger(
    service=service_name,
    level=os.getenv("LOG_LEVEL", "INFO"),
    log_record_order=["timestamp", "level", "location", "message", "xray_trace_id"]
)

# Create metrics instance
metrics = Metrics(
    service=service_name,
    namespace=f"CivicForge/{stage}"
)

# Create tracer instance
tracer = Tracer(service=service_name)

# Export configured instances
__all__ = ["logger", "metrics", "tracer"]