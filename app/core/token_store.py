from app.core.redis_client import redis_client


async def save_refresh_token(
    user_id: int, session_id: str, token: str, expire_seconds: int
):
    key = f"session:{user_id}:{session_id}"

    await redis_client.set(key, token, ex=expire_seconds)


async def get_refresh_token(user_id: int, session_id: str) -> str | None:
    key = f"session:{user_id}:{session_id}"

    token = await redis_client.get(key)

    if token is None:
        return None

    if isinstance(token, bytes):
        return token.decode()
    return token


async def delete_refresh_token(user_id: int, session_id: str) -> None:
    key = f"session:{user_id}:{session_id}"

    await redis_client.delete(key)


async def delete_all_refresh_tokens(user_id: int) -> None:
    pattern = f"session:{user_id}:*"
    async for key in redis_client.scan_iter(
        match=pattern,
    ):
        await redis_client.delete(key)
