ADR-0016: Inventory Caching and Idempotency Storage

Date: 2026-10-19 Status: Accepted

Context

Eveto caches event metadata (GET /events) in Redis to reduce database load (see ADR-0015).However, the platform also exposes ticket availability (available_quantity) and supports idempotent reservations. We must decide if these highly sensitive pieces of data should also be cached in Redis to improve performance.

Options Considered
1. Cache Inventory with a Short TTL (e.g., 5 seconds)

    What it is: Caching the available_quantity in Redis for a few seconds.
    Strengths: Reduces DB load on the GET /events/{id}/ticket-types endpoint during high traffic.
    Weaknesses: During a flash sale, 5 seconds of staleness means users will see "10 tickets available" when there are actually 0. This leads to a flood of 409 Conflict errors when they try to buy, creating a terrible user experience and breaking trust.

2. Store Idempotency Keys in Redis

    What it is: Checking Redis for the Idempotency-Key instead of Postgres.
    Strengths: Sub-millisecond lookups.
    Weaknesses: Redis is volatile. If Redis crashes or evicts the key, a retried request will bypass the idempotency check, resulting in a double-charge or duplicate reservation. This violates the core promise of idempotency.

Decision

    Do NOT cache ticket availability. The GET /events/{id}/ticket-types endpoint will always query PostgreSQL. Correctness of inventory is more important than latency.
    Store Idempotency Keys in PostgreSQL. The reservations table holds the idempotency_key with a UNIQUE constraint. This guarantees ACID compliance and ensures no double-charges occur, even during a database failover.

Consequences

    The ticket types endpoint will put more read load on Postgres. We will mitigate this via connection pooling (pool_size=20) and proper database indexing.
    Idempotency checks will take ~2ms longer than Redis, but we accept this to guarantee data integrity.

Under what conditions would this change?

If we implement a "Hold and Release" cart system where inventory is reserved for 10 minutes before payment, we might cache the cart state in Redis, but the final sold and reserved quantities will remain strictly in Postgres.