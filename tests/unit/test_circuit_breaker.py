"""Tests for the async circuit breaker.

Validates threshold behavior, state transitions, and edge cases that
match the observed production like latency data
performance investigation.

These tests assume the updated circuit_breaker.py with:
- name parameter
- call_timeout
- half_open_max_calls
- time.monotonic() (not time.time())
- CancelledError filtering
"""

import asyncio
import time

import pytest

from app.core.circuit_breaker import (
    AsyncCircuitBreaker,
    CircuitBreakerError,
)


# * Fixture
@pytest.fixture
def fast_breaker():
    """Circuit breaker with short timeouts for fast tests.

    Uses fail_max=3 and reset_timeout=0.1s to keep tests under 1 second.
    """
    return AsyncCircuitBreaker(
        name="test_service",
        fail_max=3,
        reset_timeout=0.1,  # 100ms
        call_timeout=0.5,  # 500ms
        half_open_max_calls=1,
    )


# * Helper async functions
async def always_fail(*args, **kwargs):
    raise RuntimeError("downstream failure")


async def always_succeed(*args, **kwargs):
    return "ok"


async def hang_forever(*args, **kwargs):
    """Never completes — simulates a hung downstream."""
    await asyncio.Event().wait()
    return "unreachable"


# * Initial state
@pytest.mark.asyncio
async def test_initial_state_is_closed(fast_breaker):
    assert fast_breaker.state == "closed"
    assert fast_breaker._failures == 0


# * Opens after fail_max consecutive failures
@pytest.mark.asyncio
async def test_opens_after_fail_max_consecutive_failures(fast_breaker):
    # fail_max=3 — first 2 failures keep it closed
    for i in range(2):
        with pytest.raises(RuntimeError):
            await fast_breaker.call(always_fail)
        assert (
            fast_breaker.state == "closed"
        ), f"opened too early after {i + 1} failures"

    # 3rd failure trips the breaker
    with pytest.raises(RuntimeError):
        await fast_breaker.call(always_fail)
    assert fast_breaker.state == "open"


# * Rejects calls immediately while open (fail-fast)
@pytest.mark.asyncio
async def test_rejects_calls_immediately_while_open(fast_breaker):
    # Open the breaker
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await fast_breaker.call(always_fail)
    assert fast_breaker.state == "open"

    # Next call should fail INSTANTLY with CircuitBreakerError
    # (no actual downstream call should be made)
    start = time.monotonic()
    with pytest.raises(CircuitBreakerError) as exc_info:
        await fast_breaker.call(always_succeed)
    elapsed = time.monotonic() - start

    # Should fail in < 10ms — if it took longer, the downstream was actually called
    assert elapsed < 0.01, f"took {elapsed}s — did the call actually fire?"
    assert "test_service" in str(exc_info.value)
    assert "circuit open" in str(exc_info.value).lower()


# * Transitions to half-open after reset_timeout
@pytest.mark.asyncio
async def test_transitions_to_half_open_after_reset_timeout(fast_breaker):
    # Open the breaker
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await fast_breaker.call(always_fail)
    assert fast_breaker.state == "open"

    # Wait for reset_timeout to expire
    await asyncio.sleep(0.15)  # slightly more than 0.1s

    # Next call should transition to half-open and (since it succeeds) close
    result = await fast_breaker.call(always_succeed)
    assert result == "ok"
    assert fast_breaker.state == "closed"
    assert fast_breaker._failures == 0


# * Re-opens immediately after a failed half-open call
@pytest.mark.asyncio
async def test_reopens_after_failed_half_open_call(fast_breaker):
    # Open
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await fast_breaker.call(always_fail)
    assert fast_breaker.state == "open"

    # Wait for reset
    await asyncio.sleep(0.15)

    # Failed half-open call → re-open IMMEDIATELY
    # (doesn't need to reach fail_max again — one failure in half-open = re-open)
    with pytest.raises(RuntimeError):
        await fast_breaker.call(always_fail)
    assert (
        fast_breaker.state == "open"
    ), "half-open failure should immediately re-open the breaker"

    # Subsequent calls should be rejected (circuit is open again)
    with pytest.raises(CircuitBreakerError):
        await fast_breaker.call(always_succeed)


# * Enforces call_timeout on hanging downstreams
@pytest.mark.asyncio
async def test_enforces_call_timeout(fast_breaker):
    # hang_forever never completes — should time out at call_timeout (0.5s)
    start = time.monotonic()
    with pytest.raises(asyncio.TimeoutError):
        await fast_breaker.call(hang_forever)
    elapsed = time.monotonic() - start

    # Should time out around 0.5s — if it took > 1s, the timeout didn't fire
    assert (
        0.4 < elapsed < 1.0
    ), f"hung for {elapsed}s — call_timeout didn't fire correctly"

    # The timeout counts as a downstream failure
    assert fast_breaker._failures == 1
    assert fast_breaker.state == "closed"  # 1 failure < fail_max=3


# * Does NOT count asyncio.CancelledError as a failure
@pytest.mark.asyncio
async def test_does_not_count_cancelled_error(fast_breaker):
    async def raise_cancelled():
        raise asyncio.CancelledError()

    # CancelledError should propagate but NOT count as a downstream failure
    with pytest.raises(asyncio.CancelledError):
        await fast_breaker.call(raise_cancelled)

    assert (
        fast_breaker._failures == 0
    ), "CancelledError was counted as a downstream failure"
    assert fast_breaker.state == "closed"


# * Half-open limits concurrent test calls
@pytest.mark.asyncio
async def test_half_open_limits_concurrent_calls(fast_breaker):
    # Open
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await fast_breaker.call(always_fail)
    assert fast_breaker.state == "open"

    # Wait for reset_timeout to expire
    await asyncio.sleep(0.15)

    # Slow function that takes 200ms to complete
    async def slow_succeed():
        await asyncio.sleep(0.2)
        return "ok"

    # First call transitions to half-open and starts the slow downstream call
    task1 = asyncio.create_task(fast_breaker.call(slow_succeed))

    # Yield to let task1 enter the breaker and increment half_open_in_flight
    await asyncio.sleep(0.01)

    # Second concurrent call should be rejected — half_open_max_calls=1
    with pytest.raises(CircuitBreakerError) as exc_info:
        await fast_breaker.call(always_succeed)
    assert (
        "half-open" in str(exc_info.value).lower()
    ), f"expected half-open rejection, got: {exc_info.value}"

    # Let task1 finish — should close the breaker
    result = await task1
    assert result == "ok"
    assert fast_breaker.state == "closed"


# * Successful call resets the failure counter
@pytest.mark.asyncio
async def test_success_resets_failure_counter(fast_breaker):
    # 2 failures (below threshold of 3)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await fast_breaker.call(always_fail)
    assert fast_breaker._failures == 2
    assert fast_breaker.state == "closed"

    # Success resets the counter
    result = await fast_breaker.call(always_succeed)
    assert result == "ok"
    assert fast_breaker._failures == 0
    assert fast_breaker.state == "closed"

    # 2 more failures should NOT open (counter was reset by the success)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await fast_breaker.call(always_fail)
    assert (
        fast_breaker.state == "closed"
    ), "failures before the success should not accumulate"


# * Multiple breakers with different names are independent
@pytest.mark.asyncio
async def test_multiple_breakers_are_independent():
    breaker_a = AsyncCircuitBreaker(
        name="service_a", fail_max=2, reset_timeout=0.1, call_timeout=0.5
    )
    breaker_b = AsyncCircuitBreaker(
        name="service_b", fail_max=5, reset_timeout=0.1, call_timeout=0.5
    )

    # Open breaker A (fail_max=2)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker_a.call(always_fail)
    assert breaker_a.state == "open"

    # Breaker B should be completely unaffected
    assert breaker_b.state == "closed"
    result = await breaker_b.call(always_succeed)
    assert result == "ok"


# * Error message includes time-until-retry
@pytest.mark.asyncio
async def test_error_message_includes_retry_time(fast_breaker):
    # Open the breaker
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await fast_breaker.call(always_fail)

    # Immediately rejected — message should include "s until retry"
    with pytest.raises(CircuitBreakerError) as exc_info:
        await fast_breaker.call(always_succeed)

    msg = str(exc_info.value)
    assert "test_service" in msg
    assert "until retry" in msg, f"missing retry hint in message: {msg}"


# * KeyboardInterrupt and SystemExit don't count as failure
@pytest.mark.asyncio
async def test_control_flow_exceptions_do_not_count(fast_breaker):
    async def raise_keyboard_interrupt():
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        await fast_breaker.call(raise_keyboard_interrupt)

    assert fast_breaker._failures == 0
    assert fast_breaker.state == "closed"


# * State property reflects internal state
@pytest.mark.asyncio
async def test_state_property_reflects_internal_state(fast_breaker):
    assert fast_breaker.state == "closed"

    # Open it
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await fast_breaker.call(always_fail)
    assert fast_breaker.state == "open"

    # Wait for half-open transition
    await asyncio.sleep(0.15)

    # The state should still show "open" until the next call triggers the
    # transition to "half-open" (lazy evaluation)
    assert fast_breaker.state == "open"

    # Trigger the transition
    task = asyncio.create_task(fast_breaker.call(always_succeed))
    await asyncio.sleep(0.01)  # let it enter half-open
    assert fast_breaker.state in ("half-open", "closed")  # may have already closed

    await task
    assert fast_breaker.state == "closed"


# * Repeated failures don't exceed fail_max trips in a row
@pytest.mark.asyncio
async def test_repeated_failures_dont_re_trip_after_open(fast_breaker):
    # Once open, additional failures shouldn't increment _failures unboundedly
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await fast_breaker.call(always_fail)
    assert fast_breaker.state == "open"
    failures_after_open = fast_breaker._failures
    assert failures_after_open == 3

    # While open, calls are rejected with CircuitBreakerError (not counted as failures)
    for _ in range(5):
        with pytest.raises(CircuitBreakerError):
            await fast_breaker.call(always_fail)

    # Failure counter shouldn't have grown — rejections don't count
    assert fast_breaker._failures == failures_after_open
