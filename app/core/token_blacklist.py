from app.core.redis_client import redis_client


async def blacklist_token(
    jti: str,
    expire_seconds: int,
) -> None:
    key = f"blacklist:{jti}"

    await redis_client.set(
        key,
        "true",
        ex=expire_seconds,
    )


async def is_token_blacklisted(
    jti: str,
) -> bool:
    key = f"blacklist:{jti}"

    result = await redis_client.exists(key)

    return result == 1
