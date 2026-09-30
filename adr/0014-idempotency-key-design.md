ADR-0013: Idempotency Key Design for Reservations

Date: 2026-9-30 Status: Accepted

Context

Networks are unreliable. If a user clicks "Buy Tickets" and their phone loses connection, they might click it again. If the API receives two POST /reservations requests, it must not create two reservations and double-charge the user. Similarly, the payment provider might retry a webhook delivery. We need a mechanism to safely retry requests without mutating the system state twice.
Options Considered
1. No Idempotency (Naive)

    What it is: Just process requests as they come.
    Strengths: Simple to code.
    Weaknesses: Double-charges, duplicate reservations, terrible user experience.

2. DB Unique Constraint on (User ID + Ticket Type ID)

    What it is: Forcing a user to only have one reservation per ticket type.
    Strengths: Prevents duplicates.
    Weaknesses: Too strict. A user might legitimately want to buy 2 tickets now, and 2 tickets later for their friends. This constraint would block the second purchase.

3. Client-Generated Idempotency Key Header

    What it is: The client generates a random UUID (Idempotency-Key) and sends it in the HTTP header. The server stores this key on the reservation row with a UNIQUE constraint. If a request comes in with a key that already exists, the server returns the original reservation instead of creating a new one.
    Strengths: Follows RFC standards; allows clients to safely retry any failed request; doesn't restrict legitimate future purchases.
    Weaknesses: Requires an extra DB lookup on every request; clients must generate and manage UUIDs correctly.

Decision

We choose Client-Generated Idempotency Key Header.

We will add an idempotency_key column (String, Unique, Nullable) to the reservations table. The POST /reservations endpoint will accept an Idempotency-Key header. If provided, the service will check the DB first. If a reservation exists for that key, it returns the existing one.
Consequences

    We accept the minor performance hit of an extra SELECT query on reservation creation.
    Clients must be educated to generate UUIDs for their purchase attempts.
    If a client forgets to send the key, they lose idempotency protection (the endpoint still works normally).

Under what conditions would this change?

If we integrate with a payment provider like Stripe, we will map our internal idempotency key directly to Stripe's Idempotency-Key header to ensure end-to-end protection.