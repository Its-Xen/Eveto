import time
from typing import Any, Awaitable, Callable


class CircuitBreakerError(Exception):
    """Raised when the circuit is open to protect the system."""

    pass


class AsyncCircuitBreaker:
    def __init__(self, fail_max: int = 3, reset_timeout: int = 10):
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._last_failure_time = 0.0
        self._state = "closed"  # closed, open, half-open

    async def call(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Calls an async function, protecting it with the circuit breaker."""
        if self._state == "open":
            # if the timeout has passed, try again (half-open)
            if time.time() - self._last_failure_time > self.reset_timeout:
                self._state = "half-open"
            else:
                # Circuit is open, fail instantly
                raise CircuitBreakerError(
                    "Payment provider is unavailable (Circuit open)."
                )

        try:
            result = await func(*args, **kwargs)
            # Success! Resert Everything
            self._state = "closed"
            self._failures = 0
            return result
        except Exception as e:
            # Failures! Increment Failures
            self._failures += 1
            self._last_failure_time = time.time()
            if self._failures >= self.fail_max:
                self._state = "open"
            raise e


# Our global circuit breaker for the payment provider
payment_circuit_breaker = AsyncCircuitBreaker(fail_max=3, reset_timeout=10)
