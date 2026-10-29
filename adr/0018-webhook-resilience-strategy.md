ADR-0018: Webhook Resilience Strategy

Date: 2026-10-28 Status: Accepted

Context

Eveto relies on a Mock Payment Provider to confirm reservations. This provider sends a webhook to Eveto after a payment is processed. Networks are unreliable; the provider might send the webhook twice, or Eveto's database might be down when the webhook arrives. We must guarantee that:

    A reservation is never double-confirmed (idempotency).
    A webhook is never lost, even if the DB is temporarily down.
    A flaky payment provider doesn't cascade-fail the Eveto API.

Options Considered

1. Synchronous Webhook Processing

    What it is: Process the webhook (DB updates, inventory moves) inside the HTTP request handler.
    Strengths: Simple.
    Weaknesses: If the DB is down, the webhook handler times out. The payment provider retries, causing a thundering herd. High risk of losing webhooks if the server restarts.

2. Asynchronous Processing with Idempotency Keys + Circuit Breaker

    What it is: The HTTP webhook endpoint instantly returns 200 OK and enqueues a background job. The job uses a unique provider_event_id to ensure idempotency. Calls to the payment provider are wrapped in a circuit breaker.
    Strengths: The payment provider is satisfied instantly (200 OK). The actual processing is retried automatically if the DB is down. Idempotency keys prevent double-processing.
    Weaknesses: Requires a background worker process to be running. Requires monitoring the dead-letter queue.

Decision

We choose Asynchronous Processing with Idempotency Keys + Circuit Breaker.

    Idempotency: We store the provider_event_id in a webhookevents table with a UNIQUE constraint. If a duplicate arrives, the service layer sees it already exists and returns early.
    Retry & Dead-Letter: The webhook endpoint enqueues a Dramatiq actor. If processing fails, Dramatiq retries 3x. If it still fails, we push the payload to a dead_letters Redis list for manual inspection.
    Circuit Breaker: When Eveto calls the Mock Payment Provider (during /checkout), we wrap the call in a hand-rolled AsyncCircuitBreaker. If the provider is down, the breaker trips and Eveto returns a 503 instantly, protecting our API.

Consequences

    We must ensure the Dramatiq worker is always running.
    We must monitor the /admin/dead-letters endpoint to manually fix permanently failed jobs.
    We accept that a webhook might be processed slightly after the HTTP request is acknowledged.

Under what conditions would this change?

If the payment provider implements HMAC signature verification, we would add signature validation before enqueuing the job to prevent spoofed webhooks.