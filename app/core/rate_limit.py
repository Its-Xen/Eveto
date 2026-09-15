import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

# * In-memory store: {ip_address: [timestamp1, timestamp2, ...]}
# * NOTE: This resets if the server restarts and doesn't work across multiple workers.
#! It will be replaced by a Redis-backed limiter in Week 11.

_in_memory_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 20  # 20 req
RATE_WINDOW = 60  # per 60 sec


async def check_rate_limit(request: Request) -> None:
    """Naive rate limiter for public endpoints."""

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # Filter out timestamps older than our window
    _in_memory_store[client_ip] = [
        t for t in _in_memory_store[client_ip] if now - t < RATE_WINDOW
    ]

    # Check if limit exceeded
    if len(_in_memory_store[client_ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, Please try again later",
            headers={
                "Retry-After": str(
                    int(RATE_WINDOW - (now - _in_memory_store[client_ip][0]))
                )
            },
        )

    # Record this request, ex:_in_memory_store["127.0.0.1"].append(1715469120.123)
    _in_memory_store[client_ip].append(now)
