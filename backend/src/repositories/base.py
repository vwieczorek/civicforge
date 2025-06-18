"""Base repository class with common DynamoDB operations and error handling."""
import os
from typing import Optional, Dict, Any, List, Tuple
from abc import ABC, abstractmethod
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import structlog

from ..config import REGION

logger = structlog.get_logger()


class BaseRepository(ABC):
    """Base class for all DynamoDB repositories."""
    
    def __init__(self, table_name: str):
        """Initialize repository with DynamoDB table."""
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=REGION)
        self.table = self.dynamodb.Table(table_name)
        self.logger = logger.bind(repository=self.__class__.__name__, table=table_name)
    
    async def _handle_dynamodb_error(self, error: ClientError, operation: str) -> None:
        """Handle DynamoDB errors with proper logging."""
        error_code = error.response['Error']['Code']
        self.logger.error(
            "dynamodb_error",
            operation=operation,
            error_code=error_code,
            error_message=str(error)
        )
        
        if error_code == 'ConditionalCheckFailedException':
            # Let the caller handle conditional check failures
            raise
        elif error_code == 'ResourceNotFoundException':
            raise ValueError(f"Table {self.table_name} not found")
        elif error_code in ['ProvisionedThroughputExceededException', 'RequestLimitExceeded']:
            # These should be retried with backoff
            raise
        else:
            # Re-raise other errors
            raise
    
    def _serialize_pagination_token(self, last_evaluated_key: Optional[Dict]) -> Optional[str]:
        """Serialize DynamoDB pagination token to base64 string."""
        if not last_evaluated_key:
            return None
        
        import json
        import base64
        
        token = base64.b64encode(
            json.dumps(last_evaluated_key).encode()
        ).decode()
        return token
    
    def _deserialize_pagination_token(self, token: Optional[str]) -> Optional[Dict]:
        """Deserialize base64 pagination token to DynamoDB format."""
        if not token:
            return None
        
        import json
        import base64
        
        try:
            decoded = base64.b64decode(token.encode())
            return json.loads(decoded)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            self.logger.warning("invalid_pagination_token", token=token, error=str(e))
            return None
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID. Must be implemented by subclasses."""
        pass