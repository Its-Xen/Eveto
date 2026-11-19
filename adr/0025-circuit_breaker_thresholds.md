## ADR-0025: Circuit Breaker Thresholds Tuned Against Observed Latency

Date: 2026-11-17 Status: Accepted

Related: ADR-0023 (Graceful Shutdown), ADR-0024 (Connection Pool Sizing)

## Context

The old circuit breaker implementation (app/core/circuit_breaker.py) protected payment provider calls with these thresholds:

    fail_max=3 — open after 3 consecutive failures
    reset_timeout=10 — 10s cooldown before half-open retry
    No call timeout — downstream hangs would hang the breaker
    No half-open test limiting — all queued requests would fire simultaneously when timeout expired

### Theperformance investigation produced real latency data for the first time:
| Metric | Observed Value | Source |
|--------|----------------|--------|
| Single-request latency (cache warm) | 10ms | `curl -w` timing |
| p50 latency under 100 concurrency | 245ms | wrk 30s test |
| p99 latency under 100 concurrency | 1.96s | wrk 30s test |
| Real failure rate (non-2xx/3xx) | 0.1% (16/12000) | wrk output |
| Stress failure rate (timeouts) | 0.5-0.8% (60-100/12000) | wrk output |
| Throughput | 407 RPS at 4 workers | wrk 30s test |


This data allowed a proper threshold review — the original thresholds were chosen by intuition, not measurement.

## Decision

Update AsyncCircuitBreaker thresholds and fix four implementation bugs discovered during the review.

### New Thresholds
| Threshold | Old | New | Rationale |
|-----------|-----|-----|-----------|
| `fail_max` | 3 | 5 | At 400 RPS with 0.1% failure rate, old threshold trips in ~7.5s on normal noise; new threshold tolerates ~12.5s of normal failures before opening |
| `reset_timeout` | 10s | 30s | Payment providers typically need 30s+ to recover from outages; 10s was too short and caused re-opening storms |
| `call_timeout` | (none) | 5s | Prevents slow/hung downstream from blocking request handlers; 5s is generous for payment APIs (typical p99 < 2s) |
| `half_open_max_calls` | (none) | 1 | Proper half-open semantics — only one test request probes recovery, not all queued requests |


### Implementation Bugs Fixed
| Bug | Impact | Fix |
|-----|--------|-----|
| `time.time()` for elapsed measurement | NTP clock adjustments could cause breaker to never open or open forever | Switched to `time.monotonic()` |
| No limit on concurrent half-open test calls | When timeout expired, all queued requests fired at downstream simultaneously, defeating half-open's purpose | Added `_half_open_in_flight` counter, rejects beyond `half_open_max_calls` |
| No per-call timeout | Hung downstream (very common failure mode for payment providers) would hang the breaker indefinitely, exhausting connection pool | Wrapped call in `asyncio.wait_for(timeout=call_timeout)` |
| `asyncio.CancelledError` counted as failure | Client disconnects (common under load) would increment failure counter, opening breaker on client-side issues | Explicit re-raise without incrementing failures; also filters `KeyboardInterrupt` and `SystemExit` |



### Updated Implementation

The breaker now takes a name parameter (for reusable multi-service breakers with clear error messages) and exposes a state property (for observability and testing).

payment_circuit_breaker = AsyncCircuitBreaker(    name="payment_provider",    fail_max=5,    reset_timeout=30,    call_timeout=5.0,)

## Consequences

Positive:

    Breaker no longer false-trips on normal traffic noise (~0.1% failure rate)
    Hung downstream no longer hangs request handlers (5s timeout)
    Half-open properly tests recovery with single probe instead of stampede
    Client disconnects no longer pollute the failure counter
    Multi-service breakers possible via name parameter (future webhook breaker, etc.)
    State observable via state property and Prometheus metrics (future work)

Negative:

    Slightly slower to open on real downstream outages (~12.5s vs ~7.5s at 400 RPS)
    5s call timeout may interrupt legitimately slow operations (none observed in current data, but payment provider p99 is ~2s so headroom is comfortable)
    30s reset window means failed retries take longer to attempt

Operational Implications:

    Monitor circuit_breaker_state metric (to be added in future ADR)
    Alert if breaker opens more than once per hour (indicates real downstream issue, not noise)
    Payment provider SLA: must respond within 5s or breaker will trip

## Test Coverage

Added tests/unit/test_circuit_breaker.py with 14 tests covering:
| Test | Scenario |
|------|----------|
| `test_initial_state_is_closed` | Sanity check — breaker starts closed |
| `test_opens_after_fail_max_consecutive_failures` | Threshold trip behavior |
| `test_rejects_calls_immediately_while_open` | Fail-fast (< 10ms) when open |
| `test_transitions_to_half_open_after_reset_timeout` | Timeout-based recovery |
| `test_closes_after_successful_half_open_call` | Happy path half-open → closed |
| `test_reopens_after_failed_half_open_call` | Half-open failure re-opens immediately |
| `test_enforces_call_timeout` | Hanging downstream → TimeoutError → counts as failure |
| `test_does_not_count_cancelled_error` | `asyncio.CancelledError` filtered |
| `test_half_open_limits_concurrent_calls` | Only one test probe during half-open |
| `test_success_resets_failure_counter` | Success clears accumulated failures |
| `test_multiple_breakers_are_independent` | Different `name` → independent state |
| `test_error_message_includes_retry_time` | Useful error message for clients |
| `test_control_flow_exceptions_do_not_count` | `KeyboardInterrupt` filtered |
| `test_state_property_reflects_internal_state` | Observable state for metrics |


Coverage: 96% (56 statements, 2 missed — SystemExit branch and one finally edge case). Above the 80% required threshold.

## Alternatives Considered

Keep fail_max=3 (no change)

Rejected: at 400 RPS with observed 0.1% real failure rate, 3 failures accumulate in ~7.5s — breaker would open on normal traffic noise, blocking legitimate payment attempts.

### Use failure-rate threshold instead of count (e.g., "open if >5% of last 100 requests failed")

Deferred: more sophisticated than count-based, but requires a sliding window of request outcomes. Adds complexity (memory, race conditions). Count-based with fail_max=5 is sufficient for current scale.

###  Use a library (e.g., pybreaker, aiobreaker)

Rejected: the hand-rolled implementation is small (~80 lines), well-tested, and matches our exact requirements. Adding a dependency for this would be over-engineering. The hand-rolled version also makes it easy to add custom logic (like the name parameter for multi-service breakers).

### No call_timeout (let downstream hang)

Rejected: hanging is the #1 failure mode for payment providers. Without a timeout, a single hung request would hold a DB connection and worker indefinitely, eventually exhausting the pool.

## References

- [Martin Fowler: CircuitBreaker pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Microsoft Cloud Design Patterns: Circuit Breaker](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker)
- Performance Investigation (internal — py-spy flame graphs, wrk benchmarks)
- `app/core/circuit_breaker.py` (updated implementation)
- `tests/unit/test_circuit_breaker.py` (test coverage)