import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.core.dependencies import get_optional_api_key_user, get_redis_client
from app.models.api_key import ApiKey


async def check_redis_rate_limit(
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)],
    api_key: Annotated[ApiKey | None, Depends(get_optional_api_key_user)] = None,
) -> None:
    """Redis-backed rate limiter. Limits by API Key (if present) or IP Address."""

    # * Identify the client
    if api_key:
        client_id = f"partner:{api_key.id}"
        limit = api_key.rate_limit_tier  # 10 req/min
    else:
        client_ip = request.client.host if request.client else "unknown"
        client_id = f"ip:{client_ip}"
        limit = 20  # Public endpoints get 20 req/min

    # * Create a unique Redis key for this minute
    current_minute = int(time.time() // 60)
    redis_key = f"rate_limit: {client_id}:{current_minute}"

    # * Increment the request count
    count = await redis.incr(redis_key)

    # * If it's the first reqeust, set the TTL to 60 sec
    if count == 1:
        await redis.expire(redis_key, 60)

    # ? Check if limit exceeded
    if count > limit:
        # Calculate retry-after (seconds left in the minute)
        retry_after = 60 - int(time.time() % 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit is {limit} requests per minute.",
            headers={"Retry-After": str(retry_after)},
        )
