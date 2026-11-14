ADR-0022: Tracing Tool and Instrumentation Scope

Date: 2026-11-14 Status: Accepted

Context

Eveto is a distributed system (FastAPI + Postgres + Redis + Dramatiq Worker). To debug latency and errors across these boundaries, we need distributed tracing. A single request must be traceable end-to-end.

Options Considered

1. Jaeger (Direct Export)

    What it is: Using OpenTelemetry SDK to export traces directly to Jaeger.
    Strengths: Simple setup.
    Weaknesses: Tightly couples the application to Jaeger. No intermediary processing.

2. OpenTelemetry + OTel Collector + Grafana Tempo

    What it is: App sends traces to an OTel Collector via OTLP. Collector forwards to Tempo. Grafana visualizes.
    Strengths: Decouples app from storage backend. Collector can batch, filter, and retry. Tempo integrates perfectly with Loki and Prometheus in Grafana.
    Weaknesses: More infrastructure to manage (Collector container).

Decision

We choose OpenTelemetry + OTel Collector + Grafana Tempo.

Instrumentation Scope:

    FastAPI: Auto-instrumented (creates HTTP request spans).
    SQLAlchemy: Auto-instrumented (creates DB query spans).
    Redis: Auto-instrumented (creates cache/broker spans).
    Dramatiq: Instrumented via third-party opentelemetry-instrumentor-dramatiq package to propagate trace context across the message queue, creating connected worker spans.
    Manual Spans: Used for specific business logic (e.g., process_webhook_event) if auto-instrumentation is unavailable.

Consequences

    We must run the OTel Collector and Tempo containers.
    We must manage the trace_id injection into Structlog to enable log-to-trace linking.
    The application code is decoupled from the trace storage backend.

Under what conditions would this change?

If we adopt a managed tracing service (like AWS X-Ray or Datadog), we would only need to change the OTel Collector's exporter config, not the application code.