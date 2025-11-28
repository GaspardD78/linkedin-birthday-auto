"""
Définition des métriques Prometheus pour le bot LinkedIn.
"""

from prometheus_client import Counter, Gauge, Histogram

# Compteurs (toujours croissants)
MESSAGES_SENT_TOTAL = Counter(
    "linkedin_bot_messages_sent_total",
    "Total number of birthday messages sent",
    ["status", "type"],  # status=success/failed, type=today/late
)

API_REQUESTS_TOTAL = Counter(
    "linkedin_bot_api_requests_total",
    "Total number of external API requests",
    ["endpoint", "status"],
)

# Gauges (valeurs qui fluctuent)
BIRTHDAYS_PROCESSED = Gauge(
    "linkedin_bot_birthdays_processed",
    "Number of birthdays processed in current run",
    ["type"],  # today/late/ignored
)

WEEKLY_LIMIT_REMAINING = Gauge(
    "linkedin_bot_weekly_limit_remaining", "Remaining messages allowed for the week"
)

# Histograms (distributions de durée)
RUN_DURATION_SECONDS = Histogram(
    "linkedin_bot_run_duration_seconds",
    "Time spent executing the bot run",
    buckets=[30, 60, 120, 300, 600, 900, 1800],
)

DATABASE_QUERY_DURATION = Histogram(
    "linkedin_bot_database_queries_duration", "Time spent on database queries", ["query_type"]
)
