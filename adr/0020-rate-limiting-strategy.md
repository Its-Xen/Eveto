ADR-0020: Rate Limiting Algorithm and Storage

Date: 2026-11-03S tatus: Accepted

Context

Eveto exposes public endpoints (GET /events) and Partner API endpoints (/api/v1/partners/...). To protect the PostgreSQL database from abuse, DDoS attacks, or runaway scripts, we must enforce rate limits. The system must be consistent across multiple Uvicorn workers and return proper 429 Too Many Requests responses with Retry-After headers.

Options Considered

1. In-Memory Fixed Window (Application Level)

    What it is: Tracking request counts in a Python dictionary per process.
    Strengths: Zero network latency.
    Weaknesses: Does not work in a multi-process/multi-server environment. Worker A doesn't know about Worker B's counts. State is lost on restart.

2. Token Bucket Algorithm (Redis)

    What it is: A bucket holds N tokens. Every request removes a token. Tokens are refilled at a fixed rate (e.g., 1 token/second).
    Strengths: Allows short bursts of traffic (good for web UIs that load multiple resources at once). Smooth rate limiting.
    Weaknesses: More complex to implement in Redis (requires Lua scripts for atomicity).

3. Fixed Window Counter (Redis)

    What it is: Track requests per minute using a Redis key (e.g., rate_limit:ip:1.2.3.4:1432000000). Use INCR and EXPIRE.
    Strengths: Extremely simple to implement; atomic in Redis; very fast (O(1) time complexity).
    Weaknesses: Allows bursts at the edges of the window (e.g., 20 requests at 11:59:59 and 20 more at 12:00:00).

4. Sliding Window Log (Redis)

    What it is: Store a timestamp for every request in a Redis sorted set. Query the set for requests in the last 60 seconds.
    Strengths: 100% accurate rate limiting. No edge bursts.
    Weaknesses: High memory usage; slower execution (O(log N) time complexity).

5. Load Shedding

    What it is: Not a rate limiter, but a systemic resilience pattern. When the system is overloaded (e.g., DB pool is exhausted), the server proactively rejects requests (503 Service Unavailable) to prevent a cascading failure.
    Strengths: Keeps the system alive during extreme spikes.
    Weaknesses: Requires monitoring of internal resources (DB pool size, CPU).

Decision

We choose Fixed Window Counter (Redis) for rate limiting, combined with implicit Load Shedding via our Circuit Breaker and DB Pool limits.

    Algorithm: Fixed Window Counter. For an MVP ticketing API, the simplicity and atomicity of Redis INCR/EXPIRE outweigh the edge-burst downside of the Token Bucket. If a partner exceeds their tier limit, they receive a 429 Too Many Requests with a Retry-After header indicating seconds remaining in the window.
    Storage: Redis. It is shared across all Uvicorn workers, atomic, and already part of our infrastructure.
    Load Shedding: If the database becomes overwhelmed, SQLAlchemy's connection pool will exhaust, causing requests to time out. Our graceful shutdown and circuit breaker patterns act as implicit load shedding, protecting the core system.

Consequences

    We accept that a client could theoretically send 2x the limit in a single second if they time it perfectly at the window boundary.
    We must monitor Redis memory, as rate limiting keys are created for every unique IP/API Key per minute (though they auto-expire in 60s).
    Partners are limited by their rate_limit_tier in the apikeys table.

Under what conditions would this change?

If we build a frontend UI that requires loading multiple images/API calls simultaneously and the Fixed Window causes false 429s, we would migrate to the Token Bucket algorithm to allow controlled bursts.