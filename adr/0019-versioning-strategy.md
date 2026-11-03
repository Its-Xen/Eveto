ADR-0019: API Versioning Strategy

Date: 2026-11-03 Status: Accepted

Context

As Eveto grows, the API will evolve. We may need to change response schemas, add required fields, or alter endpoint behavior. We must ensure that external partners (using the Partner API) do not break when we release updates. We need a consistent versioning strategy that is easy for external developers to use and easy for us to maintain.

Options Considered

1. URL Path Versioning (/api/v1/events)

    What it is: The version is explicitly placed in the URL path.
    Strengths: Extremely clear to developers; easy to test in browsers/Swagger; easy to route in reverse proxies (like Nginx); clients can explicitly target a specific version; visible in server logs for debugging.
    Weaknesses: Some REST purists argue the URL should represent the resource, not the version. URLs can get cluttered.

2. Query Parameter Versioning (/api/events?version=1)

    What it is: The version is passed as a query parameter.
    Strengths: Keeps the base URL path clean; easy to implement.
    Weaknesses: High risk of caching issues (CDNs often strip query params or cache them inconsistently). It is easy for clients to forget the parameter, defaulting to the wrong version. It is not explicitly visible in routing logs.

3. Media Type Negotiation / Header Versioning (Accept: application/vnd.eveto.v1+json)

    What it is: The version is passed in the HTTP Accept header using custom media types.
    Strengths: Keeps URLs perfectly clean; adheres strictly to REST/HATEOAS principles; allows content negotiation.
    Weaknesses: Hard to test in a browser; hard for partners to implement; debugging is extremely difficult because the version isn't visible in standard access logs.

Decision

We choose URL Path Versioning (/api/v1/...).

    For an API consumed by external partners, clarity and ease of use outweigh REST purity. Query parameter versioning introduces unacceptable caching risks. Media type negotiation is too opaque for simple debugging. URL path versioning makes it instantly obvious which version a client is using, simplifies Swagger UI documentation, and makes routing trivial for infrastructure.

Consequences

    All endpoints must be registered under the /api/v1 prefix.
    Breaking changes require a new /api/v2 router. The old router must be maintained until all partners migrate.
    Non-breaking changes (adding optional fields) do not require a version bump.

Under what conditions would this change?

If we move to a GraphQL or gRPC architecture, we would abandon URL versioning in favor of schema-based evolution.