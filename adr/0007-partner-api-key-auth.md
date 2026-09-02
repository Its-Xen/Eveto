ADR-0007: Partner API Key Authentication Design

Date: 2026-9-2 Status: Accepted
Context

Eveto exposes a Partner API (/api/v1/partners/...) for external systems to pull event data. Unlike internal customers and admins who log in via browsers using JWTs, partners are automated external services. They need a secure, stateless way to authenticate API requests. This authentication method will be implemented later alongside rate limiting and API versioning.
Options Considered
1. Reuse JWTs (RS256) for Partners

    What it is: Partners are given a client_id and client_secret, which they exchange for a JWT via a token endpoint.
    Strengths: Reuses existing auth infrastructure.
    Weaknesses: Requires partners to implement token refresh logic; overkill for simple read-only data pulls; doesn't natively attach metadata like "rate limit tier" to the token itself without bloating the payload.

2. Static API Keys via Custom Header (X-API-Key)

    What it is: We generate a cryptographically secure random string (the API Key). The partner passes it in an X-API-Key HTTP header. We hash it in the database and map it to a Partner account.
    Strengths: Extremely simple for partners to use; easy to revoke instantly by deleting the key from the DB; allows us to attach metadata (like rate_limit_tier and scopes) directly to the key record.
    Weaknesses: Keys must be transmitted securely (TLS); if a key is leaked, it is valid until manually rotated.

3. OAuth 2.0 Client Credentials Flow

    What it is: Full OAuth2 implementation for machine-to-machine communication.
    Strengths: Industry standard for enterprise integrations.
    Weaknesses: Massive infrastructure overhead for a simple read-only MVP API; too complex for the current scope.

Decision

We choose Static API Keys via Custom Header (X-API-Key).

For a read-only MVP partner API, static API keys provide the best balance of simplicity and control. We will create an ApiKey table in the database that stores a key_hash (using Argon2 or SHA-256), partner_name, scopes, and a rate_limit_tier. A custom FastAPI dependency will extract the X-API-Key header, hash it, look up the partner, and enforce rate limits.
Consequences

    We must build an ApiKey model and an admin UI(Swagger UI) to generate/revoke keys.
    We must implement a custom header dependency (get_api_key_user).
    We accept that we are responsible for securely generating and transmitting the keys to partners out-of-band.
    We accept that keys do not expire automatically, requiring manual rotation policies.

Under what conditions would this change?

If a partner requires fine-grained, per-user delegation (e.g., "Act on behalf of User X"), we would upgrade to OAuth 2.0. If we integrate with a major enterprise platform requiring standard machine-to-machine auth, we would adopt the OAuth 2.0 Client Credentials flow.