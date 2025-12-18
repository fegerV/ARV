"""
Simple test to debug fixture issues.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_simple_client(async_client: AsyncClient):
    """Simple test to check if client fixture works."""
    # Test basic health endpoint
    response = await async_client.get("/api/health/status")
    assert response.status_code == 200