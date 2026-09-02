ADR-0006: Refresh Token Strategy & Token Revocation

Date: 2026-9-2 Status: Accepted
Context

Eveto uses stateless JWTs for authentication. Because JWTs are self-contained and verified purely by cryptographic signature, the server does not track them in a database. This means that once a token is issued, it remains valid until its expiration time (exp), even if the user logs out, changes their password, or is banned by an admin. We need to define our strategy for handling session lifetimes and the lack of immediate token revocation.
Options Considered
1. Stateful Token Blacklist (Redis)

    What it is: Every time a user logs out or is banned, their JWT's ID (JTI) is added to a Redis blacklist. Every API request checks Redis to see if the token is revoked.
    Strengths: Immediate revocation. Secure for highly sensitive applications (banking).
    Weaknesses: Destroys the stateless nature of JWTs. Adds a Redis network lookup to every single API request, increasing latency and coupling the API to Redis uptime.

2. Short-Lived Access Tokens + Long-Lived Refresh Tokens (Stateless)

    What it is: The API issues a short-lived access token (e.g., 15–30 minutes) and a long-lived refresh token (e.g., 7 days). No blacklist is maintained.
    Strengths: Maintains pure statelessness. No extra DB/Redis lookups per request. If an access token is stolen, the attacker only has a short window of access.
    Weaknesses: No immediate revocation. If a user is banned, they can still act as a user for up to 30 minutes until their access token expires.

3. Database-Tracked Sessions (Opaque Tokens)

    What it is: Abandon JWTs entirely. Issue a random opaque string stored in a DB table. The API checks the DB on every request.
    Strengths: Instant revocation.
    Weaknesses: Defeats the purpose of choosing JWTs for a microservice architecture. High DB overhead on every request.

Decision

We choose Short-Lived Access Tokens + Long-Lived Refresh Tokens (Stateless).

For an event ticketing platform at this scale, the 15–30 minute delay in revoking a banned user is an acceptable business risk. Maintaining pure statelessness and avoiding per-request Redis lookups is a higher priority for API performance. If an admin bans a user, the admin can simply cancel the user's active reservations during that 30-minute window.
Consequences

    We accept that stolen or banned tokens remain valid for up to access_token_expire_minutes (currently 30 minutes).
    We must implement a refresh endpoint later that exchanges the refresh token for a new access token.
    Password resets do not instantly log users out across all devices.

Under what conditions would this change?

If Eveto expands into handling highly sensitive financial data or strict compliance requirements (e.g., PCI-DSS requires immediate session termination), we would migrate to a Stateful Token Blacklist (Option 1) using Redis.