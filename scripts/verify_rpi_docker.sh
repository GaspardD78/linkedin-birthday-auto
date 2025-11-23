#!/bin/bash

# ============================================================
# Raspberry Pi Docker Setup Verification Script
# ============================================================
# This script verifies that the LinkedIn Birthday Bot
# Docker Compose setup is running correctly on Raspberry Pi
# ============================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Emojis
CHECK="✓"
CROSS="✗"
INFO="ℹ"
WARN="⚠"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  LinkedIn Birthday Bot - Raspberry Pi Docker Verification ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Track overall status
ERRORS=0
WARNINGS=0

# ============================================================
# Function: Print status message
# ============================================================
print_status() {
    local status=$1
    local message=$2
    local detail=$3

    if [ "$status" = "ok" ]; then
        echo -e "${GREEN}${CHECK}${NC} ${message}"
        [ -n "$detail" ] && echo -e "  ${detail}"
    elif [ "$status" = "error" ]; then
        echo -e "${RED}${CROSS}${NC} ${message}"
        [ -n "$detail" ] && echo -e "  ${detail}"
        ((ERRORS++))
    elif [ "$status" = "warn" ]; then
        echo -e "${YELLOW}${WARN}${NC} ${message}"
        [ -n "$detail" ] && echo -e "  ${detail}"
        ((WARNINGS++))
    else
        echo -e "${BLUE}${INFO}${NC} ${message}"
        [ -n "$detail" ] && echo -e "  ${detail}"
    fi
}

# ============================================================
# 1. Check System Information
# ============================================================
echo -e "${BLUE}[1/7] System Information${NC}"
echo "─────────────────────────────────────────────────────────"

# Check if running on Raspberry Pi
if [ -f /proc/device-tree/model ]; then
    RPI_MODEL=$(cat /proc/device-tree/model)
    print_status "info" "Device: ${RPI_MODEL}"
else
    print_status "warn" "Not a Raspberry Pi or model file not found"
fi

# Check architecture
ARCH=$(uname -m)
print_status "info" "Architecture: ${ARCH}"

if [ "$ARCH" != "aarch64" ] && [ "$ARCH" != "armv7l" ]; then
    print_status "warn" "Architecture is not ARM-based (expected aarch64 or armv7l)"
fi

# Check available memory
TOTAL_MEM=$(free -h | awk 'NR==2 {print $2}')
AVAILABLE_MEM=$(free -h | awk 'NR==2 {print $7}')
print_status "info" "Memory: ${AVAILABLE_MEM} available / ${TOTAL_MEM} total"

# Check disk space
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
DISK_AVAIL=$(df -h . | awk 'NR==2 {print $4}')
if [ "$DISK_USAGE" -gt 85 ]; then
    print_status "warn" "Disk usage high: ${DISK_USAGE}% (${DISK_AVAIL} available)"
else
    print_status "ok" "Disk space: ${DISK_AVAIL} available (${DISK_USAGE}% used)"
fi

echo ""

# ============================================================
# 2. Check Docker Installation
# ============================================================
echo -e "${BLUE}[2/7] Docker Installation${NC}"
echo "─────────────────────────────────────────────────────────"

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    print_status "ok" "Docker installed: v${DOCKER_VERSION}"
else
    print_status "error" "Docker is not installed"
    echo ""
    echo -e "${RED}Please install Docker:${NC}"
    echo "  curl -fsSL https://get.docker.com | sh"
    echo "  sudo usermod -aG docker \$USER"
    exit 1
fi

if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version --short)
        print_status "ok" "Docker Compose installed: v${COMPOSE_VERSION}"
    else
        COMPOSE_VERSION=$(docker-compose --version | awk '{print $3}' | sed 's/,//')
        print_status "ok" "Docker Compose installed: v${COMPOSE_VERSION}"
    fi
else
    print_status "error" "Docker Compose is not installed"
    exit 1
fi

# Check Docker daemon
if systemctl is-active --quiet docker 2>/dev/null || pgrep dockerd &> /dev/null; then
    print_status "ok" "Docker daemon is running"
else
    print_status "error" "Docker daemon is not running"
    echo ""
    echo -e "${RED}Start Docker with:${NC}"
    echo "  sudo systemctl start docker"
    exit 1
fi

echo ""

# ============================================================
# 3. Check Docker Compose File
# ============================================================
echo -e "${BLUE}[3/7] Docker Compose Configuration${NC}"
echo "─────────────────────────────────────────────────────────"

if [ -f "docker-compose.queue.yml" ]; then
    print_status "ok" "docker-compose.queue.yml found"
else
    print_status "error" "docker-compose.queue.yml not found"
    exit 1
fi

# Check required files
if [ -f "Dockerfile.multiarch" ]; then
    print_status "ok" "Dockerfile.multiarch found"
else
    print_status "warn" "Dockerfile.multiarch not found (required for building worker)"
fi

if [ -f "auth_state.json" ]; then
    print_status "ok" "auth_state.json found"
else
    print_status "warn" "auth_state.json not found (required for LinkedIn authentication)"
fi

echo ""

# ============================================================
# 4. Check Running Containers
# ============================================================
echo -e "${BLUE}[4/7] Container Status${NC}"
echo "─────────────────────────────────────────────────────────"

# Check if compose project is running
if docker-compose -f docker-compose.queue.yml ps &> /dev/null || docker compose -f docker-compose.queue.yml ps &> /dev/null; then
    # Use docker compose if available, fallback to docker-compose
    if docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi

    # Get container status
    REDIS_STATUS=$($COMPOSE_CMD -f docker-compose.queue.yml ps -q redis 2>/dev/null | xargs -r docker inspect -f '{{.State.Status}}' 2>/dev/null || echo "not running")
    WORKER_STATUS=$($COMPOSE_CMD -f docker-compose.queue.yml ps -q rq-worker 2>/dev/null | xargs -r docker inspect -f '{{.State.Status}}' 2>/dev/null || echo "not running")

    # Redis container
    if [ "$REDIS_STATUS" = "running" ]; then
        print_status "ok" "Redis container: running"
    else
        print_status "error" "Redis container: ${REDIS_STATUS}"
    fi

    # Worker container
    if [ "$WORKER_STATUS" = "running" ]; then
        print_status "ok" "RQ Worker container: running"
    else
        print_status "error" "RQ Worker container: ${WORKER_STATUS}"
    fi
else
    print_status "error" "Docker Compose project not running"
    echo ""
    echo -e "${YELLOW}Start the containers with:${NC}"
    echo "  docker-compose -f docker-compose.queue.yml up -d"
    ERRORS=$((ERRORS + 2))
fi

echo ""

# ============================================================
# 5. Check Redis Health
# ============================================================
echo -e "${BLUE}[5/7] Redis Health Check${NC}"
echo "─────────────────────────────────────────────────────────"

if [ "$REDIS_STATUS" = "running" ]; then
    # Check Redis connectivity
    if docker exec linkedin-bot-redis redis-cli ping &> /dev/null; then
        print_status "ok" "Redis responding to PING"

        # Get Redis info
        REDIS_VERSION=$(docker exec linkedin-bot-redis redis-cli INFO SERVER | grep redis_version | cut -d: -f2 | tr -d '\r')
        print_status "info" "Redis version: ${REDIS_VERSION}"

        REDIS_MEM=$(docker exec linkedin-bot-redis redis-cli INFO MEMORY | grep used_memory_human | cut -d: -f2 | tr -d '\r')
        print_status "info" "Redis memory usage: ${REDIS_MEM}"

        # Check for keys
        KEY_COUNT=$(docker exec linkedin-bot-redis redis-cli DBSIZE | awk '{print $2}')
        print_status "info" "Redis keys: ${KEY_COUNT}"
    else
        print_status "error" "Redis not responding to PING"
    fi
else
    print_status "error" "Cannot check Redis health - container not running"
fi

echo ""

# ============================================================
# 6. Check Worker Health
# ============================================================
echo -e "${BLUE}[6/7] Worker Health Check${NC}"
echo "─────────────────────────────────────────────────────────"

if [ "$WORKER_STATUS" = "running" ]; then
    # Check worker logs for errors
    WORKER_LOGS=$(docker logs linkedin-bot-worker --tail 20 2>&1)

    if echo "$WORKER_LOGS" | grep -qi "error\|exception\|failed\|traceback"; then
        print_status "warn" "Worker logs contain errors (check logs for details)"
        echo ""
        echo -e "${YELLOW}Recent worker logs:${NC}"
        docker logs linkedin-bot-worker --tail 10 2>&1 | sed 's/^/  /'
    else
        print_status "ok" "Worker logs look healthy"
    fi

    # Check if worker is connected to Redis
    if echo "$WORKER_LOGS" | grep -qi "connected to redis\|redis connection"; then
        print_status "ok" "Worker connected to Redis"
    else
        print_status "info" "Worker Redis connection status unclear"
    fi
else
    print_status "error" "Cannot check worker health - container not running"
fi

echo ""

# ============================================================
# 7. Expected Warnings
# ============================================================
echo -e "${BLUE}[7/7] Expected Warnings${NC}"
echo "─────────────────────────────────────────────────────────"

print_status "info" "Checking for known expected warnings..."

# Check for Redis memory warning
REDIS_LOGS=$(docker logs linkedin-bot-redis --tail 50 2>&1 || echo "")
if echo "$REDIS_LOGS" | grep -qi "memory soft limit\|overcommit_memory"; then
    print_status "warn" "Redis memory warning detected (EXPECTED on Raspberry Pi)"
    echo -e "  ${YELLOW}This is documented and expected. To fix (optional):${NC}"
    echo -e "  ${YELLOW}sudo sysctl vm.overcommit_memory=1${NC}"
    echo -e "  ${YELLOW}To make permanent, add to /etc/sysctl.conf:${NC}"
    echo -e "  ${YELLOW}vm.overcommit_memory = 1${NC}"
else
    print_status "ok" "No Redis memory warnings"
fi

echo ""

# ============================================================
# Summary
# ============================================================
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                         SUMMARY                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}${CHECK} All checks passed! Your setup is ready.${NC}"
    echo ""
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}${WARN} Setup is working but has ${WARNINGS} warning(s).${NC}"
    echo ""
else
    echo -e "${RED}${CROSS} Found ${ERRORS} error(s) and ${WARNINGS} warning(s).${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting steps:${NC}"
    echo ""
    echo "1. View container logs:"
    echo "   docker logs linkedin-bot-redis"
    echo "   docker logs linkedin-bot-worker"
    echo ""
    echo "2. Restart containers:"
    echo "   docker-compose -f docker-compose.queue.yml restart"
    echo ""
    echo "3. Rebuild containers:"
    echo "   docker-compose -f docker-compose.queue.yml down"
    echo "   docker-compose -f docker-compose.queue.yml build --no-cache"
    echo "   docker-compose -f docker-compose.queue.yml up -d"
    echo ""
fi

echo -e "${BLUE}Quick Commands:${NC}"
echo "  View Redis logs:    docker logs linkedin-bot-redis -f"
echo "  View Worker logs:   docker logs linkedin-bot-worker -f"
echo "  Container status:   docker-compose -f docker-compose.queue.yml ps"
echo "  Restart services:   docker-compose -f docker-compose.queue.yml restart"
echo "  Stop services:      docker-compose -f docker-compose.queue.yml down"
echo ""

exit $ERRORS
