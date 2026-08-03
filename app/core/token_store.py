from app.core.redis_client import redis_client


async def save_refresh_token(user_id: int, token: str, expire_seconds: int):
    key = f"refresh:{user_id}"

    await redis_client.set(key, token, ex=expire_seconds)


async def get_refresh_token(user_id: int) -> str | None:
    key = f"refresh:{user_id}"

    token = await redis_client.get(key)

    if token is None:
        return None

    if isinstance(token, bytes):
        return token.decode()
    return token


async def delete_refresh_token(user_id: int) -> None:
    key = f"refresh:{user_id}"

    await redis_client.delete(key)
