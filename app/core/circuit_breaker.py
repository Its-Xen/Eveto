import asyncio
import time
from typing import Any, Awaitable, Callable


class CircuitBreakerError(Exception):
    """Raised when the circuit is open to protect the system."""

    pass


class AsyncCircuitBreaker:
    """Async circuit breaker with half-open limiting, call timeout, and
    proper exception filtering.

    Thresholds tuned against observed production-like latency data
      - fail_max=5: tolerates ~0.1% transient failure rate without false trips
      - reset_timeout=30: payment providers typically need 30s to recover
      - call_timeout=5: prevents slow downstream from hanging requests
      - half_open_max_calls=1: only one test request during half-open
    """

    def __init__(
        self,
        name: str = "default",
        fail_max: int = 5,
        reset_timeout: int = 30,
        call_timeout: float = 5.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.call_timeout = call_timeout
        self.half_open_max_calls = half_open_max_calls

        self._failures = 0
        self._last_failure_time: float = 0.0
        self._state = "closed"  # closed, open, half-open
        self._half_open_in_flight = 0

    @property
    def state(self) -> str:
        return self._state

    async def call(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Calls an async function, protected by the circuit breaker.

        Raises:
            CircuitBreakerError: If the circuit is open or half-open is saturated.
            asyncio.TimeoutError: If the wrapped call exceeds call_timeout.
            Exception: Re-raises any exception from the wrapped function.
        """
        # Check state before making the call
        if self._state == "open":
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.reset_timeout:
                self._state = "half-open"
                self._half_open_in_flight = 0
            else:
                raise CircuitBreakerError(
                    f"{self.name} unavailable (circuit open, "
                    f"{self.reset_timeout - int(elapsed)}s until retry)"
                )

        # Limit concurrent half-open test calls
        if self._state == "half-open":
            if self._half_open_in_flight >= self.half_open_max_calls:
                raise CircuitBreakerError(
                    f"{self.name} unavailable (half-open: testing recovery)"
                )
            self._half_open_in_flight += 1

        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.call_timeout,
            )
            # Success! Reset everything
            self._failures = 0
            if self._state == "half-open":
                self._state = "closed"
            return result
        except asyncio.CancelledError:
            # Client cancelled — NOT a downstream failure, don't count
            raise
        except asyncio.TimeoutError:
            # Downstream hung — this IS a failure
            self._record_failure()
            raise
        except Exception as e:
            # Don't count control-flow exceptions as downstream failures
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            self._record_failure()
            raise
        finally:
            if self._state == "half-open":
                self._half_open_in_flight = max(0, self._half_open_in_flight - 1)

    def _record_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.monotonic()

        if self._state == "half-open":
            # Half-open failure → immediately re-open the breaker
            self._state = "open"
        elif self._failures >= self.fail_max:
            self._state = "open"


# Global circuit breaker for the payment provider
# Tuned against observed latency data (ADR-0025):
# - fail_max=5: at 400 RPS with 0.1% failure rate, takes ~12.5s to trip
#              (was 3 / ~7.5s — too sensitive to normal noise)
# - reset_timeout=30: payment providers typically need 30s to recover
#              (was 10 — too short for real provider outages)
# - call_timeout=5: prevents slow provider from hanging requests
#              (was unbounded — could hang forever)
payment_circuit_breaker = AsyncCircuitBreaker(
    name="payment_provider",
    fail_max=5,
    reset_timeout=30,
    call_timeout=5.0,
)
