"""AWS Lambda Powertools idempotency configuration for CivicForge."""
import os
from typing import Dict, Any, Optional
from aws_lambda_powertools.utilities.idempotency import (
    IdempotencyConfig,
    DynamoDBPersistenceLayer,
    idempotent,
    idempotent_function
)
from aws_lambda_powertools.utilities.idempotency.exceptions import (
    IdempotencyAlreadyInProgressError,
    IdempotencyItemAlreadyExistsError
)
import structlog

logger = structlog.get_logger()

# Initialize persistence layer with DynamoDB
persistence_layer = DynamoDBPersistenceLayer(
    table_name=os.environ.get("IDEMPOTENCY_TABLE", "civicforge-dev-idempotency")
)

# Configure idempotency settings
config = IdempotencyConfig(
    expires_after_seconds=3600,  # 1 hour expiration
    event_key_jmespath="body",  # Use request body as idempotency key by default
    use_local_cache=True,       # Cache results in Lambda memory
    local_cache_max_items=256,  # Limit memory usage
    hash_function="md5"         # Fast hashing for idempotency keys
)


def make_idempotent(
    event_key_jmespath: Optional[str] = None,
    expires_after_seconds: Optional[int] = None
):
    """
    Decorator to make Lambda handlers idempotent.
    
    Args:
        event_key_jmespath: JMESPath expression to extract idempotency key
        expires_after_seconds: Override default expiration time
    
    Example:
        @make_idempotent(event_key_jmespath="questId")
        def handler(event, context):
            # Process quest creation
            return {"statusCode": 200}
    """
    custom_config = IdempotencyConfig(
        expires_after_seconds=expires_after_seconds or config.expires_after_seconds,
        event_key_jmespath=event_key_jmespath or config.event_key_jmespath,
        use_local_cache=config.use_local_cache,
        local_cache_max_items=config.local_cache_max_items,
        hash_function=config.hash_function
    )
    
    return idempotent(
        config=custom_config,
        persistence_store=persistence_layer
    )


def make_idempotent_function(
    data_keyword_argument: str,
    expires_after_seconds: Optional[int] = None
):
    """
    Decorator to make individual functions idempotent.
    
    Args:
        data_keyword_argument: Name of the argument to use as idempotency key
        expires_after_seconds: Override default expiration time
    
    Example:
        @make_idempotent_function(data_keyword_argument="quest_id")
        async def create_quest(quest_id: str, quest_data: dict):
            # Process quest creation
            return quest
    """
    custom_config = IdempotencyConfig(
        expires_after_seconds=expires_after_seconds or config.expires_after_seconds,
        use_local_cache=config.use_local_cache,
        local_cache_max_items=config.local_cache_max_items,
        hash_function=config.hash_function
    )
    
    return idempotent_function(
        data_keyword_argument=data_keyword_argument,
        config=custom_config,
        persistence_store=persistence_layer
    )


class IdempotencyHandler:
    """
    Context manager for handling idempotency in non-decorator scenarios.
    
    Example:
        async with IdempotencyHandler("unique-key-123") as handler:
            if handler.is_cached:
                return handler.cached_result
            
            # Do work
            result = process_payment()
            
            handler.save_result(result)
            return result
    """
    
    def __init__(
        self,
        idempotency_key: str,
        expires_after_seconds: int = 3600
    ):
        self.key = idempotency_key
        self.expires = expires_after_seconds
        self.is_cached = False
        self.cached_result = None
        self._in_progress = False
        
    async def __aenter__(self):
        try:
            # Try to get existing result
            result = persistence_layer.get_record(
                idempotency_key=self.key
            )
            if result:
                self.is_cached = True
                self.cached_result = result
                logger.info(
                    "idempotency_cache_hit",
                    idempotency_key=self.key
                )
        except IdempotencyItemAlreadyExistsError:
            self.is_cached = True
            self.cached_result = persistence_layer.get_record(
                idempotency_key=self.key
            )
        except IdempotencyAlreadyInProgressError:
            logger.warning(
                "idempotency_in_progress",
                idempotency_key=self.key
            )
            raise
        except Exception as e:
            logger.error(
                "idempotency_check_failed",
                idempotency_key=self.key,
                error=str(e)
            )
            # Continue without idempotency on error
            
        if not self.is_cached:
            # Mark as in progress
            try:
                persistence_layer.save_inprogress(
                    idempotency_key=self.key,
                    expires_after_seconds=self.expires
                )
                self._in_progress = True
            except Exception as e:
                logger.error(
                    "idempotency_save_inprogress_failed",
                    idempotency_key=self.key,
                    error=str(e)
                )
                
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type and self._in_progress:
            # Delete in-progress record on error
            try:
                persistence_layer.delete_record(
                    idempotency_key=self.key
                )
            except Exception as e:
                logger.error(
                    "idempotency_cleanup_failed",
                    idempotency_key=self.key,
                    error=str(e)
                )
    
    def save_result(self, result: Any):
        """Save the result for future idempotent calls."""
        if self._in_progress:
            try:
                persistence_layer.save_success(
                    idempotency_key=self.key,
                    result=result,
                    expires_after_seconds=self.expires
                )
                logger.info(
                    "idempotency_result_saved",
                    idempotency_key=self.key
                )
            except Exception as e:
                logger.error(
                    "idempotency_save_failed",
                    idempotency_key=self.key,
                    error=str(e)
                )


# Common idempotency configurations for different operations

# Quest creation - idempotent for 24 hours based on quest ID
quest_creation_idempotent = make_idempotent(
    event_key_jmespath="body.questId",
    expires_after_seconds=86400  # 24 hours
)

# Reward processing - idempotent for 7 days based on reward ID
reward_processing_idempotent = make_idempotent(
    event_key_jmespath="Records[0].body.rewardId",
    expires_after_seconds=604800  # 7 days
)

# User creation - idempotent for 1 hour based on user ID (Cognito trigger)
user_creation_idempotent = make_idempotent(
    event_key_jmespath="request.userAttributes.sub",
    expires_after_seconds=3600  # 1 hour
)

# Attestation - idempotent for 24 hours based on quest ID + user ID
attestation_idempotent = make_idempotent(
    event_key_jmespath="[body.questId, body.userId]",
    expires_after_seconds=86400  # 24 hours
)