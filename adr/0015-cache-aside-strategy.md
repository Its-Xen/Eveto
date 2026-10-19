ADR-0015: Cache-aside Strategy and Invalidation

Date: 2026-10-19 Status: Accepted

Context

Eveto's public API (GET /events) receives the vast majority of read traffic. To protect the PostgreSQL database and reduce latency, we need to cache these reads in Redis. However, because this is a ticketing platform, reading stale inventory (available tickets) during a flash sale is a critical business failure. We must decide what to cache, and how to invalidate it.

Options Considered
1. Cache-aside with TTL (Lazy Expiration)

    What it is: Cache data for 5 minutes. Wait for it to expire naturally.
    Strengths: Extremely simple.
    Weaknesses: An admin could update an event's title, and users would see the old title for up to 5 minutes. Unacceptable for metadata changes.

2. Write-through

    What it is: Every DB write also updates the Redis cache.
    Strengths: Cache is never stale.
    Weaknesses: Writes are slower; complex to implement for nested objects; risks race conditions if the DB write succeeds but the cache write fails.

3. Cache-aside with Explicit Versioned Invalidation

    What it is: Cache data with a TTL. On any write (Create/Update/Delete), increment a global events:version key in Redis. All cache keys include this version (e.g., events:list:v12:0:100). When the version increments, old keys are orphaned and expire via TTL.
    Strengths: Reads are fast; writes are fast (a single INCR command); cache is instantly invalidated for all users.
    Weaknesses: Slightly more complex logic in the service layer.

Decision

We choose Cache-aside with Explicit Versioned Invalidation for event metadata (GET /events and GET /events/{id}).

We deliberately DO NOT CACHE ticket availability (GET /events/{id}/ticket-types). The available_quantity changes on every reservation, and relying on a cache for this volatile data risks overselling or falsely showing "Sold Out". Inventory math must always hit the database to guarantee accuracy under concurrency.
Consequences

    Admin changes to events are reflected instantly to public users.
    Ticket availability will always be live, causing slightly higher DB load on the ticket types endpoint, which is an acceptable trade-off for correctness.
    Orphaned cache keys will consume a tiny amount of Redis memory until their TTL expires (max 5 minutes).

Under what conditions would this change?

If we implement a Redis-backed rate limiter or session store that requires strict consistency, we might evaluate write-through for user-specific data. For event data, this pattern is optimal.

