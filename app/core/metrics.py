from prometheus_client import Counter, Gauge

active_db_connections = Gauge(
    "active_db_connections", "Number of active DB connections in the pool"
)
reservation_conflicts_total = Counter(
    "reservation_conflicts_total",
    "Total number of reservation conflicts (oversell attempts)",
)

# Cache Hit/Miss Counters
cache_hits_total = Counter("cache_hits_total", "Total number of cache hits")
cache_misses_total = Counter("cache_misses_total", "Total number of cache misses")
