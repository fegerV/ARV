"""Unit tests for OAuth state management."""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from app.utils.oauth_state import OAuthStateStore


@pytest.fixture
def oauth_state_store():
    """Create a fresh OAuthStateStore instance for each test."""
    return OAuthStateStore()


class TestOAuthStateStore:
    """Test cases for OAuthStateStore."""

    @pytest.mark.asyncio
    async def test_create_state_in_memory(self, oauth_state_store):
        """Test creating state in memory when Redis is unavailable."""
        # Ensure Redis client is None
        oauth_state_store._redis_client = None
        
        state = await oauth_state_store.create_state("test_connection", user_id=123)
        
        assert state is not None
        assert len(state) > 0
        assert state in oauth_state_store._memory_store
        
        stored_data = oauth_state_store._memory_store[state]
        assert stored_data["connection_name"] == "test_connection"
        assert stored_data["metadata"]["user_id"] == 123
        assert "timestamp" in stored_data

    @pytest.mark.asyncio
    async def test_create_state_with_redis(self, oauth_state_store):
        """Test creating state with Redis available."""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        
        with patch.object(oauth_state_store, '_get_redis_client', return_value=mock_redis):
            state = await oauth_state_store.create_state("test_connection")
            
            assert state is not None
            mock_redis.setex.assert_called_once()
            
            # Verify the call arguments
            call_args = mock_redis.setex.call_args
            assert call_args[0][0].startswith("oauth_state:")
            assert call_args[0][1] == 300  # TTL
            import json
            stored_data = json.loads(call_args[0][2])
            assert stored_data["connection_name"] == "test_connection"

    @pytest.mark.asyncio
    async def test_get_and_delete_state_success(self, oauth_state_store):
        """Test successful state retrieval and deletion."""
        # Create state in memory
        state = await oauth_state_store.create_state("test_connection", user_id=123)
        
        # Retrieve and delete
        retrieved_data = await oauth_state_store.get_and_delete_state(state)
        
        assert retrieved_data is not None
        assert retrieved_data["connection_name"] == "test_connection"
        assert retrieved_data["metadata"]["user_id"] == 123
        assert state not in oauth_state_store._memory_store

    @pytest.mark.asyncio
    async def test_get_and_delete_state_not_found(self, oauth_state_store):
        """Test retrieving non-existent state."""
        result = await oauth_state_store.get_and_delete_state("non_existent_state")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_and_delete_state_expired(self, oauth_state_store):
        """Test retrieving expired state."""
        # Create state
        state = await oauth_state_store.create_state("test_connection")
        
        # Manually expire the state
        oauth_state_store._memory_store[state]["timestamp"] = time.time() - 400  # 400 seconds ago
        
        # Try to retrieve
        result = await oauth_state_store.get_and_delete_state(state)
        assert result is None
        assert state not in oauth_state_store._memory_store

    @pytest.mark.asyncio
    async def test_cleanup_expired_states(self, oauth_state_store):
        """Test cleanup of expired states."""
        # Create multiple states
        state1 = await oauth_state_store.create_state("test1")
        state2 = await oauth_state_store.create_state("test2")
        state3 = await oauth_state_store.create_state("test3")
        
        # Manually expire some states
        oauth_state_store._memory_store[state1]["timestamp"] = time.time() - 400
        oauth_state_store._memory_store[state2]["timestamp"] = time.time() - 350
        # state3 remains valid
        
        # Cleanup
        cleaned_count = await oauth_state_store.cleanup_expired_states()
        
        assert cleaned_count == 2
        assert state1 not in oauth_state_store._memory_store
        assert state2 not in oauth_state_store._memory_store
        assert state3 in oauth_state_store._memory_store

    @pytest.mark.asyncio
    async def test_is_state_valid_true(self, oauth_state_store):
        """Test state validation for valid state."""
        state = await oauth_state_store.create_state("test_connection")
        
        is_valid = await oauth_state_store.is_state_valid(state)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_is_state_valid_false_not_found(self, oauth_state_store):
        """Test state validation for non-existent state."""
        is_valid = await oauth_state_store.is_state_valid("non_existent")
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_is_state_valid_false_expired(self, oauth_state_store):
        """Test state validation for expired state."""
        state = await oauth_state_store.create_state("test_connection")
        
        # Manually expire the state
        oauth_state_store._memory_store[state]["timestamp"] = time.time() - 400
        
        is_valid = await oauth_state_store.is_state_valid(state)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_redis_fallback_to_memory(self, oauth_state_store):
        """Test fallback to memory when Redis fails."""
        # Mock Redis that fails on setex but works on ping
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis error"))
        
        with patch.object(oauth_state_store, '_get_redis_client', return_value=mock_redis):
            state = await oauth_state_store.create_state("test_connection")
            
            # Should fallback to memory
            assert state in oauth_state_store._memory_store
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, oauth_state_store):
        """Test handling of Redis connection failure."""
        with patch.object(oauth_state_store, '_get_redis_client', return_value=None):
            state = await oauth_state_store.create_state("test_connection")
            
            # Should use memory store
            assert state in oauth_state_store._memory_store
            assert oauth_state_store._redis_available is False

    @pytest.mark.asyncio
    async def test_get_and_delete_state_with_redis_success(self, oauth_state_store):
        """Test state retrieval with Redis."""
        mock_redis = AsyncMock()
        test_data = {"connection_name": "test", "timestamp": time.time()}
        mock_redis.get = AsyncMock(return_value='{"connection_name": "test"}')
        mock_redis.delete = AsyncMock()
        
        with patch.object(oauth_state_store, '_get_redis_client', return_value=mock_redis):
            result = await oauth_state_store.get_and_delete_state("test_state")
            
            assert result is not None
            assert result["connection_name"] == "test"
            mock_redis.get.assert_called_once_with("oauth_state:test_state")
            mock_redis.delete.assert_called_once_with("oauth_state:test_state")

    @pytest.mark.asyncio
    async def test_get_and_delete_state_with_redis_fallback(self, oauth_state_store):
        """Test Redis fallback to memory for state retrieval."""
        # Create state in memory first
        state = await oauth_state_store.create_state("test_connection")
        
        # Mock Redis that fails
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
        
        with patch.object(oauth_state_store, '_get_redis_client', return_value=mock_redis):
            result = await oauth_state_store.get_and_delete_state(state)
            
            # Should fallback to memory
            assert result is not None
            assert result["connection_name"] == "test_connection"
            assert state not in oauth_state_store._memory_store