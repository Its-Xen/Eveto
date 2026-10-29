ADR-0017: Background Task Queue Choice (Dramatiq)

Date: 2026-10-28 Status: Accepted

Context

Eveto requires a background task queue to handle asynchronous operations: sending confirmation emails, processing payment webhooks, and running periodic cleanup jobs (sweepers). The system must guarantee "at-least-once" delivery, automatic retries with exponential backoff, and dead-letter queueing for failed jobs.

Options Considered
1. Celery

    What it is: The de facto standard Python task queue.
    Strengths: Massive ecosystem, battle-tested, supports complex routing, widely understood by engineers.
    Weaknesses: Heavyweight; historically struggles with native asyncio support (requires running a separate event loop thread); configuration can feel like a "black box" with hidden states; uses a custom JSON serializer by default.

2. RQ (Redis Queue)

    What it is: A lightweight, simple Python library for queuing jobs.
    Strengths: Extremely simple API; easy to monitor; minimal configuration.
    Weaknesses: Lacks built-in support for complex middleware, sophisticated retry logic, or dead-letter queues. Too simple for a system requiring strict resilience.

3. Dramatiq

    What it is: A fast and reliable distributed task processing library.
    Strengths: Clean, decorator-based API; robust built-in middleware (Retries, AgeLimits, etc.); supports dead-lettering natively; handles asyncio integration more cleanly than Celery (by allowing asyncio.run inside actors); fast.
    Weaknesses: Smaller community compared to Celery; fewer third-party integrations.

Decision

We choose Dramatiq.

For a modern, async-first FastAPI application, Celery's asyncio integration can be brittle. Dramatiq provides the enterprise-grade reliability (retries, dead-letter queues) of Celery without the bloat. Its middleware system allowed us to easily implement a custom dead-letter path (dead_letters Redis list) and its simple actor model integrates cleanly with our service layer.
Consequences

    Developers must use asyncio.run() to call async service functions from sync Dramatiq actors (which can cause event loop pooling issues, requiring careful engine management).
    The system relies on Redis as the broker, which is already part of our stack.
    We avoid the Celery "serializers" and configuration overhead.

Under what conditions would this change?

If we scale to a point where we need complex task routing (e.g., different queues for CPU-bound vs I/O-bound tasks across multiple worker pools) and Celery resolves its native asyncio support, we might reconsider Celery.