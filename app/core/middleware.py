import time
import uuid
from collections.abc import MutableMapping
from typing import Any

import structlog
from starlette.types import ASGIApp, Receive, Scope, Send
from structlog.contextvars import bind_contextvars, clear_contextvars

logger = structlog.get_logger()


class RequestIDMiddleware:
    """Pure ASGI middleware to manage Request IDs and logging context."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"x-request-id":
                request_id = header_value.decode("latin-1")
                break

        if not request_id:
            request_id = uuid.uuid4().hex

        bind_contextvars(request_id=request_id)

        async def send_with_request_id(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start":
                old_headers = message.get("headers", [])
                new_headers = list(old_headers)
                # * force Python to create a brand new list in memory.
                # * copy the existing headers into it, add our x-request-id header,
                # * and then assign that new list back to the message.
                new_headers.append((b"x-request-id", request_id.encode("latin-1")))

                message["headers"] = new_headers

            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            clear_contextvars()


class TimingMiddleware:
    """Pure ASGI middleware to measure request duration
    and add X-Response-Time header"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()

        async def send_with_timing(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start":
                # Calculate duration
                duration = time.perf_counter() - start_time
                duration_ms = f"{duration * 1000:.2f}ms"

                # Add a response headers
                old_headers = message.get("headers", [])
                new_headers = list(old_headers)
                new_headers.append((b"x-response-time", duration_ms.encode("latin-1")))
                message["headers"] = new_headers

                # * WIRE TO PROMETHEUS HOOK IN WEEK 12
                # * For now, we log it. The RequestIDMiddleware will automatically
                # * attach the request_id to this log because of contextvars!
                logger.info("Request completed", response_time=duration_ms)

            await send(message)

        await self.app(scope, receive, send_with_timing)
