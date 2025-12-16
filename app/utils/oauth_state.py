"""OAuth state management for Yandex Disk OAuth flow with Redis fallback to memory store."""

import json
import secrets
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from app.core.config import get_settings

settings = get_settings()


class OAuthStateStore:
    """Manages OAuth state tokens with Redis fallback to in-memory storage."""
    
    def __init__(self):
        self._memory_store: Dict[str, Dict[str, Any]] = {}
        self._ttl_seconds = 300  # 5 minutes
    
    async def create_state(self, connection_name: str, **metadata: Any) -> str:
        """Create a new OAuth state token and store associated data."""
        state = secrets.token_urlsafe(32)
        state_data = {
            "connection_name": connection_name,
            "timestamp": time.time(),
            "metadata": metadata,
        }

        self._memory_store[state] = state_data
        return state
    
    async def get_and_delete_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Get state data and delete it (one-time use)."""
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
        if state in self._memory_store:
            current_time = time.time()
            return current_time - self._memory_store[state]["timestamp"] <= self._ttl_seconds
        
        return False


# Global instance
oauth_state_store = OAuthStateStore()