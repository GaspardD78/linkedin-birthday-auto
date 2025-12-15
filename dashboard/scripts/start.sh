#!/bin/bash
set -e

# Configuration
# Note: In docker-compose.pi4-standalone.yml, redis service is named 'redis-bot'
# Dashboard connects to 'redis-dashboard' for its own cache, but needs 'redis-bot' for worker status.
# The requirement is explicitly to wait for 'redis-bot:6379'.
REDIS_HOST="${BOT_REDIS_HOST:-redis-bot}"
REDIS_PORT="${BOT_REDIS_PORT:-6379}"
TIMEOUT=60

echo "🚀 Starting Dashboard Entrypoint..."
echo "🔌 Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."

start_ts=$(date +%s)
while :; do
    if (echo > /dev/tcp/$REDIS_HOST/$REDIS_PORT) >/dev/null 2>&1; then
        echo "✅ Redis is ready!"
        break
    fi

    current_ts=$(date +%s)
    elapsed=$((current_ts - start_ts))

    if [ $elapsed -ge $TIMEOUT ]; then
        echo "❌ Timeout: Redis not ready after $TIMEOUT seconds."
        exit 1
    fi

    echo "⏳ Waiting for Redis... (${elapsed}s/${TIMEOUT}s)"
    sleep 2
done

# Optional: Run migrations if needed (placeholder as requested)
# echo "🔄 Running database migrations..."
# npx prisma migrate deploy || true

echo "🟢 Starting application..."
exec "$@"
