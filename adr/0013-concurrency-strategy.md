ADR-0013: Concurrency Strategy for Inventory

Date: 2026-9-30 Status: Accepted

Context

Eveto's core business logic is ticket reservation. During a flash sale, hundreds of users might attempt to buy the last few tickets for an event at the exact same millisecond. We must guarantee that total_quantity is never breached (overselling). Because we run multiple Uvicorn workers (processes), Python's asyncio.Lock is useless here. The locking must happen at the database level.
Options Considered
1. Pessimistic Locking (SELECT ... FOR UPDATE)

    What it is: When a transaction queries the ticket inventory, Postgres places a hard lock on that row. Other transactions trying to read/update that row must wait in line until the first transaction commits or rolls back.
    Strengths: 100% guarantee against overselling; no retry logic needed in the application code; simple mental model (lock -> check -> update -> commit).
    Weaknesses: Can cause lock contention (waiting in line) under extreme load, slightly reducing throughput.

2. Optimistic Locking (Version Column)

    What it is: Adding a version integer to the row. The transaction reads the row, does math in Python, and tries to update: UPDATE ... WHERE id = 1 AND version = 5. If 0 rows are updated, it means someone else changed it, and the transaction must abort and retry.
    Strengths: No database locks; high throughput when collisions are rare.
    Weaknesses: In a flash sale (high collision), almost all transactions will fail and retry. This causes a "retry storm" that wastes CPU and can crash the database.

Decision

We choose Pessimistic Locking (SELECT ... FOR UPDATE).

In a ticketing platform, correctness is more important than maximum throughput. Overselling 10 VIP tickets is a catastrophic business failure. Pessimistic locking forces concurrent requests into a single-file line, guaranteeing the math is always perfectly accurate. The slight latency from lock contention is an acceptable trade-off for zero overselling.
Consequences

    We accept that under extreme load, requests might take slightly longer to complete due to lock queues.
    We must ensure our DB connection pool is adequately sized, as connections will be held while waiting for locks.
    We must ensure transactions are as short as possible to release locks quickly.

Under what conditions would this change?

If we move to a system where inventory is massive (e.g., millions of units) and exact counts don't matter (e.g., likes on a social media post), we would switch to Optimistic Locking or append-only event sourcing.