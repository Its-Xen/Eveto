ADR-0008: Pagination Strategy

Date: 2026-9-13 Status: Accepted

Context

Eveto exposes list endpoints (GET /events, GET /admin/venues). Without pagination, querying these endpoints would return entire database tables. As the platform grows, this would consume excessive memory and network bandwidth, causing slow API responses and potential crashes.
Options Considered
1. Offset/Limit Pagination (Traditional)

    What it is: Clients pass skip=0&limit=20. The database uses OFFSET 0 LIMIT 20.
    Strengths: Extremely simple to implement in SQL and SQLAlchemy; easy for clients to jump to specific "pages" (e.g., skip=40).
    Weaknesses: "Slow Paging" - if a new record is inserted while the user is paging, OFFSET shifts and they see duplicate items. Performance degrades on large OFFSET values because the DB still scans skipped rows.

2. Cursor-Based Pagination (Keyset)

    What it is: Clients pass after=<last_item_id>. The database uses WHERE id > <last_item_id> LIMIT 20.
    Strengths: Constant time performance regardless of page depth; immune to data shifting (no duplicate items).
    Weaknesses: Cannot jump to arbitrary pages (no "Go to Page 5"); more complex to implement, especially with sorted non-ID fields.

Decision

We choose Offset/Limit Pagination.

For an MVP ticketing platform, the number of events and venues is relatively small. The simplicity of Offset/Limit and the ability for admins to jump to specific pages outweighs the performance concerns of deep pagination.
Consequences

    We accept the risk of duplicate items if data is inserted during pagination.
    We will cap limit at a maximum value (e.g., 100) to prevent clients from requesting massive datasets.

Under what conditions would this change?

If we implement infinite scrolling on a frontend, or if the events table grows to millions of rows causing OFFSET latency to spike, we will migrate to Cursor-Based pagination.