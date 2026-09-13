ADR-0009: Error Response Schema

Date: 2026-9-13 Status: Accepted

Context

When an API request fails (e.g., 404 Not Found, 401 Unauthorized, 422 Validation Error), the client needs a consistent, machine-readable format to understand what went wrong. Inconsistent error formats force frontend developers to write custom parsing logic for every endpoint.
Options Considered
1. FastAPI Default ({"detail": "..."})

    What it is: FastAPI's built-in error format. It returns {"detail": "Error message"}.
    Strengths: Requires zero configuration. Supported by Swagger UI out of the box.
    Weaknesses: detail is sometimes a string (404) and sometimes an array (422 Validation), which is annoying for clients to parse.

2. RFC 7807 (Problem Details for HTTP APIs)

    What it is: A standardized format ({"type": "...", "title": "...", "status": 404, "detail": "..."}).
    Strengths: Industry standard, highly structured.
    Weaknesses: Requires custom exception handlers to map all FastAPI exceptions to this format. Overkill for a simple MVP.

3. Custom Envelope ({"error": {"code": "...", "message": "..."}})

    What it is: Wrapping errors in a specific error object with machine-readable codes.
    Strengths: Great for frontend i18n (translating error codes to localized strings).
    Weaknesses: Requires building a mapping of all error codes.

Decision

We choose FastAPI Default ({"detail": "..."}) for the MVP.

To maintain consistency, we will ensure our custom exceptions (like NotFoundError and ConflictError) always pass a string to the detail field. 
Consequences

    We accept that 422 Validation errors will return an array in detail, while 404/401 errors return a string.
    Frontend clients will need to handle this slight type difference.

Under what conditions would this change?

If we build a public SDK for external partners, we will implement custom exception handlers to map all errors to RFC 7807 to provide a strictly typed, standardized contract.