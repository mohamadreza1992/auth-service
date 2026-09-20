import time

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


async def mark_refresh_token_rotated(
    jti: str,
    expire_seconds: int,
) -> None:
    key = f"refresh-rotation:{jti}"

    await redis_client.set(
        key,
        str(time.time()),
        ex=expire_seconds,
    )


async def get_refresh_token_rotation_time(
    jti: str,
) -> float | None:
    key = f"refresh-rotation:{jti}"

    value = await redis_client.get(key)

    if value is None:
        return None

    return float(value)
