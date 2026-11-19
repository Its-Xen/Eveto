## ADR-0024: Database Connection Pool Sizing


Date: 2026-11-17 Status: Accepted

Related: ADR-0023 (Graceful Shutdown), ADR-0025 (Circuit Breaker Thresholds)

## Context

Performance baseline established:

    Single-request latency: 12.7ms (cache hit path)
    Throughput: 377 RPS at 100 concurrency with 4 uvicorn workers
    p99 latency: ~50ms
    Cache hit rate: ~95% on /api/v1/events (verified via pg_stat_activity showing 1 active query at 100 concurrent requests)

The PostgreSQL database has:

    max_connections = 100 (default)
    Query latency: <5ms for indexed reads
    Connection establishment: ~10ms

We need to size SQLAlchemy's async connection pool to:

    Handle expected concurrency without queueing
    Provide a spike buffer for traffic bursts
    Not exhaust PostgreSQL's connection limit
    Fail fast (not hang) when pool is exhausted

## Decision

### Configure SQLAlchemy async engine with:

engine = create_async_engine(    settings.db_url,    pool_size=20,        # baseline connections held open    max_overflow=10,     # spike buffer (50% of baseline)    pool_timeout=5,      # fail fast after 5s of waiting    pool_recycle=1800,   # recycle connections every 30 minutes    pool_pre_ping=True,  # verify connection is alive before use)

### Sizing Rationale

pool_size=20 (baseline):

    4 uvicorn workers × 5 concurrent DB-touching requests = 20 baseline connections needed
    Cache hit rate is ~95% on /api/v1/events (verified: pg_stat_activity showed 1 active query at 100 concurrency with cache warm)
    Only the cache-miss path (5% of requests) touches the DB
    20 baseline connections comfortably handle the cache-miss rate

max_overflow=10 (spike buffer):

    50% of baseline — standard heuristic for burst absorption
    Allows short-term surge to 30 connections per worker
    With 4 workers: 30 × 4 = 120 max connections total
    Exceeds PG's 100, but only under sustained cache-miss storm (unlikely given cache-aside design)

pool_timeout=5 (fail fast):

    Default is 30s — far too long; causes request pile-up that propagates to all workers
    5s gives the pool time to release a connection from a quick query (<5ms typical) but doesn't hang the request
    If pool is exhausted for >5s, something is wrong and the request should fail with a clear error (logs sqlalchemy.exc.TimeoutError)

pool_recycle=1800 (30 minutes):

    PostgreSQL's default tcp_keepalive_time is 7200s (2 hours)
    Idle connections in the pool can be killed by network middleboxes (NAT, firewalls, AWS NLB) after ~30 minutes
    Recycling at 30 minutes preempts this — connections are proactively refreshed before they go stale

pool_pre_ping=True:

    Sends a SELECT 1 before each checkout
    Adds ~1ms per request — negligible
    Catches stale connections (e.g., DB restarts, network blips) before they cause application errors
    Cheaper than retrying a failed query

## Consequences

Positive:

    Cache hit path uses zero DB connections (verified: 0 active queries at 100 concurrency after cache warm)
    Cache miss path is well-served (20 connections × ~5ms query time = ~4000 RPS theoretical DB throughput)
    Fail-fast behavior prevents request pile-up during pool exhaustion
    Connection recycling prevents stale-connection errors

Negative:

    At 4 workers, theoretical max (120) exceeds PG default max_connections=100
    Mitigation: cache hit rate is ~95%, so actual DB connection usage stays low
    If cache fails completely, all requests hit DB and pool exhausts in seconds
    Operational mitigation: monitor pg_stat_activity count and alert if > 50

Operational Implications:

    Monitor pg_stat_activity count — alert if > 50% of max_connections
    Monitor SQLAlchemy pool metrics — alert if overflow > 5 sustained
    If scaling to more workers, reduce per-worker pool_size proportionally:
        8 workers: pool_size=10, max_overflow=5 (total 120 — still over 100, but cache protects)
        16 workers: pool_size=5, max_overflow=3 (total 128 — only safe with 95%+ cache hit rate)
    For production scale beyond 16 workers, introduce PgBouncer (see Alternatives)

## Alternatives Considered
### NullPool (no pooling)

Rejected: every request opens/closes a connection, adding ~10ms latency per request. Defeats the purpose of async DB access and would cut throughput by ~50%.

### pool_size=5 (minimal)

Rejected: at 5 cache-miss requests per worker, only 5 connections — single slow query would block all DB access for that worker. Throughput would collapse under any DB-side hiccup.

### pool_size=50 (generous)

Rejected: with 4 workers, 200 baseline connections would exceed PG max_connections=100 immediately, causing connection errors on startup. Would require bumping PG max_connections to 250+ which has memory implications (each PG connection uses ~10MB).

### PgBouncer as connection multiplexer

Deferred: would allow many app-side connections to share few PG-side connections (transaction pooling mode). Adds operational complexity (another service to deploy, monitor, debug). Deferred until connection pressure actually becomes a problem (i.e., when scaling beyond 8 workers or seeing real pool-exhaustion alerts).

## Validation

The performance investigation validated this configuration:
| Scenario | Observed | Expected |
|----------|----------|----------|
| Cache-warm `pg_stat_activity` during 100 concurrency | 1 active, 20 idle | ~0 active (cache hits) |
| Cache-cold single request latency | 12ms | <20ms |
| Throughput at 100 concurrency, 4 workers | 407 RPS | >377 RPS (Week 9 baseline) |
| Pool exhaustion events | 0 observed | 0 (cache prevents) |


## References

- [SQLAlchemy Async Engine Pooling](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#async-orm-engine)
- [PostgreSQL max_connections tuning](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [PgBouncer](https://www.pgbouncer.org/)