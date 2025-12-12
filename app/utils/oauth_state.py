"""OAuth state management for Yandex Disk OAuth flow with Redis fallback to memory store."""

import json
import secrets
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

import redis.asyncio as redis
from app.core.config import get_settings

settings = get_settings()


class OAuthStateStore:
    """Manages OAuth state tokens with Redis fallback to in-memory storage."""
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._memory_store: Dict[str, Dict[str, Any]] = {}
        self._ttl_seconds = 300  # 5 minutes
        self._redis_available = False
    
    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client, return None if unavailable."""
        if self._redis_client is not None:
            return self._redis_client if self._redis_available else None
        
        try:
            self._redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            await self._redis_client.ping()
            self._redis_available = True
            return self._redis_client
        except Exception:
            self._redis_available = False
            self._redis_client = None
            return None
    
    async def create_state(self, connection_name: str, **metadata: Any) -> str:
        """Create a new OAuth state token and store associated data."""
        state = secrets.token_urlsafe(32)
        state_data = {
            "connection_name": connection_name,
            "timestamp": time.time(),
            "metadata": metadata,
        }
        
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                await redis_client.setex(
                    f"oauth_state:{state}",
                    self._ttl_seconds,
                    json.dumps(state_data)
                )
                return state
            except Exception:
                # Fallback to memory store
                pass
        
        # Memory store fallback
        self._memory_store[state] = state_data
        return state
    
    async def get_and_delete_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Get state data and delete it (one-time use)."""
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                data = await redis_client.get(f"oauth_state:{state}")
                if data:
                    await redis_client.delete(f"oauth_state:{state}")
                    return json.loads(data)
            except Exception:
                # Fallback to memory store
                pass
        
        # Memory store fallback
        if state in self._memory_store:
            data = self._memory_store.pop(state)
            return data
        
        return None
    
    async def cleanup_expired_states(self) -> int:
        """Clean up expired states from memory store. Returns count of cleaned items."""
        current_time = time.time()
        expired_keys = [
            key for key, value in self._memory_store.items()
            if current_time - value["timestamp"] > self._ttl_seconds
        ]
        
        for key in expired_keys:
            del self._memory_store[key]
        
        return len(expired_keys)
    
    async def is_state_valid(self, state: str) -> bool:
        """Check if state exists and is not expired."""
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                exists = await redis_client.exists(f"oauth_state:{state}")
                return bool(exists)
            except Exception:
                # Fallback to memory store
                pass
        
        # Memory store fallback
        if state in self._memory_store:
            current_time = time.time()
            return current_time - self._memory_store[state]["timestamp"] <= self._ttl_seconds
        
        return False


# Global instance
oauth_state_store = OAuthStateStore()