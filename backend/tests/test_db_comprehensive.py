"""
Comprehensive unit tests for db.py - testing database layer without AWS mocking
Focus on serialization, validation, and business logic
"""

import pytest
from datetime import datetime
from src.db import DynamoDBClient
from src.models import Quest, QuestStatus, User, FailedReward, Attestation


def test_dynamodb_client_initialization():
    """Test DynamoDB client initialization."""
    client = DynamoDBClient()
    assert client.users_table_name == "test-users"
    assert client.quests_table_name == "test-quests" 
    assert client.failed_rewards_table_name == "test-failed-rewards"


def test_serialize_item_comprehensive():
    """Test comprehensive serialization of various data types."""
    client = DynamoDBClient()
    
    test_data = {
        'string_field': 'test_value',
        'integer_field': 42,
        'float_field': 3.14,
        'boolean_true': True,
        'boolean_false': False,
        'null_field': None,
        'empty_string': '',
        'zero_value': 0,
        'list_field': [1, 'two', True, None],
        'dict_field': {'nested_key': 'nested_value', 'nested_int': 123},
        'set_field': {'item1', 'item2', 'item3'},
        'complex_nested': {
            'level1': {
                'level2': ['a', 'b', {'level3': True}]
            }
        }
    }
    
    serialized = client._serialize_item(test_data)
    
    # Verify serialization format
    assert serialized['string_field'] == {'S': 'test_value'}
    assert serialized['integer_field'] == {'N': '42'}
    assert serialized['float_field'] == {'N': '3.14'}
    assert serialized['boolean_true'] == {'BOOL': True}
    assert serialized['boolean_false'] == {'BOOL': False}
    assert serialized['null_field'] == {'NULL': True}
    assert serialized['empty_string'] == {'S': ''}
    assert serialized['zero_value'] == {'N': '0'}
    assert 'L' in serialized['list_field']
    assert 'M' in serialized['dict_field']
    assert 'SS' in serialized['set_field']


def test_deserialize_item_comprehensive():
    """Test comprehensive deserialization of DynamoDB format."""
    client = DynamoDBClient()
    
    serialized_data = {
        'string_field': {'S': 'test_value'},
        'integer_field': {'N': '42'},
        'float_field': {'N': '3.14'},
        'boolean_true': {'BOOL': True},
        'boolean_false': {'BOOL': False},
        'null_field': {'NULL': True},
        'empty_string': {'S': ''},
        'zero_value': {'N': '0'},
        'list_field': {'L': [{'N': '1'}, {'S': 'two'}, {'BOOL': True}, {'NULL': True}]},
        'dict_field': {'M': {'nested_key': {'S': 'nested_value'}, 'nested_int': {'N': '123'}}},
        'set_field': {'SS': ['item1', 'item2', 'item3']},
        'unknown_type': {'UNKNOWN': 'should_return_none'}
    }
    
    deserialized = client._deserialize_item(serialized_data)
    
    # Verify deserialization
    assert deserialized['string_field'] == 'test_value'
    assert deserialized['integer_field'] == 42
    assert deserialized['float_field'] == 3.14
    assert deserialized['boolean_true'] is True
    assert deserialized['boolean_false'] is False
    assert deserialized['null_field'] is None
    assert deserialized['empty_string'] == ''
    assert deserialized['zero_value'] == 0
    assert deserialized['list_field'] == [1, 'two', True, None]
    assert deserialized['dict_field'] == {'nested_key': 'nested_value', 'nested_int': 123}
    assert deserialized['set_field'] == {'item1', 'item2', 'item3'}
    assert deserialized['unknown_type'] is None


def test_serialize_value_edge_cases():
    """Test serialization of edge case values."""
    client = DynamoDBClient()
    
    # Test various numeric formats
    assert client._serialize_value(0) == {'N': '0'}
    assert client._serialize_value(-42) == {'N': '-42'}
    assert client._serialize_value(3.14159) == {'N': '3.14159'}
    assert client._serialize_value(float('inf')) == {'N': 'inf'}
    
    # Test boolean values
    assert client._serialize_value(True) == {'BOOL': True}
    assert client._serialize_value(False) == {'BOOL': False}
    
    # Test None
    assert client._serialize_value(None) == {'NULL': True}
    
    # Test empty collections
    assert client._serialize_value([]) == {'L': []}
    assert client._serialize_value({}) == {'M': {}}
    assert client._serialize_value(set()) == {'SS': []}
    
    # Test nested structures
    nested = {'inner': [1, {'deep': True}]}
    serialized_nested = client._serialize_value(nested)
    assert serialized_nested == {
        'M': {
            'inner': {
                'L': [
                    {'N': '1'},
                    {'M': {'deep': {'BOOL': True}}}
                ]
            }
        }
    }


def test_deserialize_value_edge_cases():
    """Test deserialization of edge case values."""
    client = DynamoDBClient()
    
    # Test numeric edge cases
    assert client._deserialize_value({'N': '0'}) == 0
    assert client._deserialize_value({'N': '-42'}) == -42
    assert client._deserialize_value({'N': '3.14'}) == 3.14
    assert client._deserialize_value({'N': '1.23e-4'}) == 1.23e-4
    
    # Test boolean values
    assert client._deserialize_value({'BOOL': True}) is True
    assert client._deserialize_value({'BOOL': False}) is False
    
    # Test null
    assert client._deserialize_value({'NULL': True}) is None
    
    # Test string set
    assert client._deserialize_value({'SS': ['a', 'b', 'c']}) == {'a', 'b', 'c'}
    assert client._deserialize_value({'SS': []}) == set()
    
    # Test unknown type returns None
    assert client._deserialize_value({'UNKNOWN_TYPE': 'value'}) is None
    
    # Test empty DynamoDB value
    assert client._deserialize_value({}) is None


def test_roundtrip_serialization():
    """Test that serialize -> deserialize produces original data."""
    client = DynamoDBClient()
    
    original_data = {
        'quest_id': 'quest-123',
        'creator_id': 'user-456',
        'title': 'Test Quest',
        'description': 'A test quest for verification',
        'reward_xp': 100,
        'reward_reputation': 10,
        'status': 'OPEN',
        'created_at': '2023-01-01T00:00:00Z',
        'attestations': [],
        'metadata': {
            'tags': ['test', 'verification'],
            'priority': 'high',
            'estimated_time': 2.5
        },
        'participants': {'creator-123', 'performer-456'},
        'flags': {
            'is_urgent': True,
            'is_public': False,
            'requires_signature': None
        }
    }
    
    # Serialize then deserialize
    serialized = client._serialize_item(original_data)
    roundtrip_data = client._deserialize_item(serialized)
    
    # Compare results (sets need special handling)
    assert roundtrip_data['quest_id'] == original_data['quest_id']
    assert roundtrip_data['creator_id'] == original_data['creator_id']
    assert roundtrip_data['title'] == original_data['title']
    assert roundtrip_data['reward_xp'] == original_data['reward_xp']
    assert roundtrip_data['status'] == original_data['status']
    assert roundtrip_data['attestations'] == original_data['attestations']
    assert roundtrip_data['metadata'] == original_data['metadata']
    assert roundtrip_data['participants'] == original_data['participants']
    assert roundtrip_data['flags'] == original_data['flags']


def test_quest_model_to_dynamodb_serialization():
    """Test serialization of actual Quest model data."""
    client = DynamoDBClient()
    
    # Create a Quest with various data types
    quest = Quest(
        questId="quest-789",
        creatorId="creator-123",
        title="Complex Quest",
        description="A quest with various data types for testing serialization",
        status=QuestStatus.SUBMITTED,
        performerId="performer-456",
        rewardXp=250,
        rewardReputation=25,
        createdAt=datetime(2023, 1, 1, 12, 0, 0),
        claimedAt=datetime(2023, 1, 2, 12, 0, 0),
        submittedAt=datetime(2023, 1, 3, 12, 0, 0),
        submissionText="Work completed successfully",
        attestations=[
            Attestation(
                user_id="creator-123",
                role="requestor", 
                attested_at=datetime(2023, 1, 4, 12, 0, 0),
                signature="0x1234567890abcdef"
            ),
            Attestation(
                user_id="performer-456",
                role="performer",
                attested_at=datetime(2023, 1, 4, 13, 0, 0)
            )
        ]
    )
    
    # Convert to dict (similar to what would be stored)
    quest_dict = quest.model_dump()
    
    # Test serialization doesn't crash and produces expected format
    serialized = client._serialize_item(quest_dict)
    
    assert 'questId' in serialized
    assert 'creatorId' in serialized
    assert 'status' in serialized
    assert 'attestations' in serialized
    
    # Verify specific field types
    assert serialized['questId']['S'] == "quest-789"
    assert serialized['rewardXp']['N'] == "250"
    assert serialized['status']['S'] == "SUBMITTED"
    assert 'L' in serialized['attestations']  # List of attestations


def test_user_model_serialization():
    """Test serialization of User model data."""
    client = DynamoDBClient()
    
    user = User(
        userId="user-123",
        username="testuser",
        walletAddress="0x742d35Cc6638C0532C2BF8C8f18fAe2C7B67E4A3",
        reputation=150,
        experience=2500,
        questCreationPoints=8,
        createdAt=datetime(2023, 1, 1),
        updatedAt=datetime(2023, 1, 15)
    )
    
    user_dict = user.model_dump()
    serialized = client._serialize_item(user_dict)
    
    assert serialized['userId']['S'] == "user-123"
    assert serialized['username']['S'] == "testuser"
    assert serialized['reputation']['N'] == "150"
    assert serialized['experience']['N'] == "2500"
    assert serialized['questCreationPoints']['N'] == "8"


def test_failed_reward_model_serialization():
    """Test serialization of FailedReward model data."""
    client = DynamoDBClient()
    
    failed_reward = FailedReward(
        recordId="failure-123",
        userId="user-456",
        questId="quest-789",
        xp=100,
        reputation=10,
        error="DynamoDB timeout",
        status="pending",
        createdAt=datetime(2023, 1, 1),
        retryCount=2
    )
    
    reward_dict = failed_reward.model_dump()
    serialized = client._serialize_item(reward_dict)
    
    assert serialized['recordId']['S'] == "failure-123"
    assert serialized['userId']['S'] == "user-456"
    assert serialized['xp']['N'] == "100"
    assert serialized['retryCount']['N'] == "2"
    assert serialized['status']['S'] == "pending"


def test_serialize_datetime_conversion():
    """Test datetime object serialization."""
    client = DynamoDBClient()
    
    now = datetime(2023, 6, 15, 14, 30, 45)
    data_with_datetime = {
        'timestamp': now,
        'iso_string': now.isoformat(),
        'mixed_data': {
            'created': now,
            'name': 'test'
        }
    }
    
    serialized = client._serialize_item(data_with_datetime)
    
    # datetime objects should be converted to strings
    assert serialized['timestamp']['S'] == now.isoformat()
    assert serialized['iso_string']['S'] == now.isoformat()
    assert serialized['mixed_data']['M']['created']['S'] == now.isoformat()
    assert serialized['mixed_data']['M']['name']['S'] == 'test'


def test_quest_computed_properties_in_serialization():
    """Test that Quest computed properties work correctly with serialization."""
    client = DynamoDBClient()
    
    quest = Quest(
        questId="computed-test",
        creatorId="creator-123",
        title="Computed Properties Test",
        description="Testing computed properties",
        createdAt=datetime.utcnow(),
        attestations=[
            Attestation(user_id="creator-123", role="requestor", attested_at=datetime.utcnow()),
            Attestation(user_id="performer-456", role="performer", attested_at=datetime.utcnow())
        ]
    )
    
    # Test computed properties
    assert quest.attester_ids == ["creator-123", "performer-456"]
    assert quest.has_requestor_attestation is True
    assert quest.has_performer_attestation is True
    
    # Test serialization includes computed values when dumped
    quest_dict = quest.model_dump()
    serialized = client._serialize_item(quest_dict)
    
    # Verify attestations are properly serialized
    assert 'L' in serialized['attestations']
    assert len(serialized['attestations']['L']) == 2


def test_serialization_performance_large_data():
    """Test serialization performance with larger data structures."""
    client = DynamoDBClient()
    
    # Create large-ish data structure
    large_data = {
        'id': 'performance-test',
        'large_list': list(range(100)),
        'large_dict': {f'key_{i}': f'value_{i}' for i in range(50)},
        'nested_structure': {
            'level1': {
                'level2': {
                    'items': [{'id': i, 'name': f'item_{i}'} for i in range(20)]
                }
            }
        },
        'set_data': {f'item_{i}' for i in range(30)}
    }
    
    # This should complete without errors or excessive delay
    serialized = client._serialize_item(large_data)
    deserialized = client._deserialize_item(serialized)
    
    # Verify key structure is preserved
    assert deserialized['id'] == 'performance-test'
    assert len(deserialized['large_list']) == 100
    assert len(deserialized['large_dict']) == 50
    assert len(deserialized['set_data']) == 30
    assert len(deserialized['nested_structure']['level1']['level2']['items']) == 20


def test_serialization_with_special_characters():
    """Test serialization with special characters and unicode."""
    client = DynamoDBClient()
    
    special_data = {
        'unicode_text': 'Hello 世界 🌍',
        'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?',
        'escaped_quotes': 'String with "quotes" and \'apostrophes\'',
        'newlines_and_tabs': 'Line 1\nLine 2\tTabbed',
        'emoji_set': {'🚀', '⭐', '🎯'},
        'mixed_unicode': {
            'japanese': 'こんにちは',
            'arabic': 'مرحبا',
            'emoji': '🎉'
        }
    }
    
    serialized = client._serialize_item(special_data)
    deserialized = client._deserialize_item(serialized)
    
    # Verify all special characters are preserved
    assert deserialized['unicode_text'] == 'Hello 世界 🌍'
    assert deserialized['special_chars'] == '!@#$%^&*()_+-=[]{}|;:,.<>?'
    assert deserialized['escaped_quotes'] == 'String with "quotes" and \'apostrophes\''
    assert deserialized['newlines_and_tabs'] == 'Line 1\nLine 2\tTabbed'
    assert deserialized['emoji_set'] == {'🚀', '⭐', '🎯'}
    assert deserialized['mixed_unicode']['japanese'] == 'こんにちは'
    assert deserialized['mixed_unicode']['arabic'] == 'مرحبا'
    assert deserialized['mixed_unicode']['emoji'] == '🎉'