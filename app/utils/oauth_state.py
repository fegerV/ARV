"""OAuth state management for Yandex Disk OAuth flow with Redis backing and in-memory fallback."""

import secrets
import time
from typing import Dict, Optional, Any

from app.core.config import get_settings
from app.core.redis import redis_client

settings = get_settings()

_OAUTH_STATE_PREFIX = "oauth_state:"
_TTL_SECONDS = 300  # 5 minutes


class OAuthStateStore:
    """Manages OAuth state tokens in Redis with TTL, falling back to in-memory storage."""

    def __init__(self):
        self._memory_store: Dict[str, Dict[str, Any]] = {}
        self._ttl_seconds = _TTL_SECONDS
        self._redis_available: Optional[bool] = None

    async def _check_redis(self) -> bool:
        """Check if Redis is available. Cache result to avoid repeated connection attempts."""
        if self._redis_available is not None:
            return self._redis_available
        try:
            await redis_client.ping()
            self._redis_available = True
            return True
        except Exception:
            self._redis_available = False
            return False

    async def create_state(self, connection_name: str, **metadata: Any) -> str:
        """Create a new OAuth state token and store associated data."""
        state = secrets.token_urlsafe(32)
        state_data = {
            "connection_name": connection_name,
            "timestamp": time.time(),
            "metadata": metadata,
        }

        if await self._check_redis():
            try:
                await redis_client.setex(
                    _OAUTH_STATE_PREFIX + state,
                    self._ttl_seconds,
                    _encode_state(state_data),
                )
                return state
            except Exception:
                self._redis_available = False

        self._memory_store[state] = state_data
        return state

    async def get_and_delete_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Get state data and delete it (one-time use)."""
        if await self._check_redis():
            try:
                raw = await redis_client.get(_OAUTH_STATE_PREFIX + state)
                if raw is not None:
                    await redis_client.delete(_OAUTH_STATE_PREFIX + state)
                    return _decode_state(raw)
            except Exception:
                self._redis_available = False

        if state in self._memory_store:
            data = self._memory_store.pop(state)
            return data

        return None

    async def cleanup_expired_states(self) -> int:
        """Clean up expired states from memory store. Returns count of cleaned items.

        Note: Redis TTL handles automatic expiration, so this only cleans memory store.
        """
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
        if await self._check_redis():
            try:
                if await redis_client.exists(_OAUTH_STATE_PREFIX + state) == 1:
                    return True
            except Exception:
                self._redis_available = False

        if state in self._memory_store:
            current_time = time.time()
            return current_time - self._memory_store[state]["timestamp"] <= self._ttl_seconds

        return False


def _encode_state(state_data: Dict[str, Any]) -> str:
    """Encode state data to a storable string."""
    import json
    return json.dumps(state_data)


def _decode_state(raw: str) -> Dict[str, Any]:
    """Decode state data from stored string."""
    import json
    return json.loads(raw)


# Global instance
oauth_state_store = OAuthStateStore()
