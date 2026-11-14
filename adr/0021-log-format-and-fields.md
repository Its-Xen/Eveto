ADR-0021: Log Format and Fields

Date: 2026-11-14 Status: Accepted

Context

Eveto requires structured logging to enable log aggregation, search, and correlation with distributed traces. Logs must be machine-readable and contain enough context to debug issues without attaching a debugger.

Options Considered

1. Plain Text Logs (print statements or basic logging)

    What it is: 2026-11-14 12:00:00 INFO User 123 logged in
    Strengths: Easy to read in a terminal.
    Weaknesses: Impossible to parse reliably in log aggregation tools (Loki/Datadog). No structured fields.

2. Python logging with python-json-logger

    What it is: Using the standard library logging module with a JSON formatter.
    Strengths: Better than plain text.
    Weaknesses: Requires passing context variables (like request_id) manually through the logging hierarchy, which is brittle.

3. structlog with JSONRenderer

    What it is: A dedicated structured logging library that uses contextvars to automatically bind request-scoped data.
    Strengths: Automatically injects request_id, trace_id, and span_id into every log line without manual passing. Renders pure JSON.
    Weaknesses: Adds a dependency.

Decision

We choose structlog with JSONRenderer.

Every log line will be a JSON object containing at minimum:

    timestamp: ISO 8601 format.
    event: The log message/action.
    level: Log level (info, warning, error).
    request_id: Automatically injected by middleware.
    trace_id / span_id: Automatically injected by a custom OTel processor, enabling log-to-trace linking in Grafana.

Consequences

    Logs are harder to read in a raw terminal (require jq or a log viewer).
    We must configure Structlog processors carefully to ensure context vars are merged.

Under what conditions would this change?

If we move to a cloud provider with a proprietary logging agent that requires a specific format, we would adjust the renderer.