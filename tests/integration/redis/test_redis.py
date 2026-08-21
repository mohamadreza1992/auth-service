import pytest


@pytest.mark.asyncio
async def test_redis_connection(redis_client):
    result = await redis_client.ping()
    assert result is True
