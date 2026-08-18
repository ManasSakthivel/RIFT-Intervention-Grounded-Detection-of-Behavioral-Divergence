#!/usr/bin/env bash
# RIFT Testbed Startup Script — Phase 3.6 §4
# Status: READY_FOR_LINUX
#
# Starts the complete RIFT evaluation testbed:
#   - Online Boutique microservices
#   - OTEL Collector
#   - Prometheus
#   - Jaeger
#
# Requirements:
#   - Linux (Docker with NET_ADMIN capability)
#   - Docker Engine >= 24
#   - Docker Compose >= 2.20
#
# Usage:
#   ./scripts/start_testbed.sh [--profile dev|val]
#
# This script DETECTS Linux requirements and refuses execution on macOS.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_DIR="$REPO_ROOT/docker"

# ── Platform check ────────────────────────────────────────────────────────────
OS="$(uname -s)"
if [[ "$OS" != "Linux" ]]; then
    echo "ERROR: start_testbed.sh requires Linux." >&2
    echo "  Detected OS: $OS" >&2
    echo "  Status: READY_FOR_LINUX" >&2
    echo "  This script cannot run on macOS or Windows." >&2
    echo "  Provision a Linux environment and re-run." >&2
    exit 1
fi

echo "==> RIFT Testbed Startup"
echo "    Platform: $OS (PASS)"

# ── Dependency checks ─────────────────────────────────────────────────────────
for tool in docker tc kubectl; do
    if ! command -v "$tool" &>/dev/null; then
        echo "WARNING: '$tool' not found. Some features may be unavailable." >&2
    else
        echo "    $tool: $(command -v $tool) (FOUND)"
    fi
done

# Check NET_ADMIN capability
if [[ $(id -u) -ne 0 ]] && ! capsh --print 2>/dev/null | grep -q cap_net_admin; then
    echo "WARNING: CAP_NET_ADMIN not detected. tc netem interventions will fail." >&2
    echo "  Run as root or with --cap-add NET_ADMIN" >&2
fi

# ── Export build metadata ─────────────────────────────────────────────────────
export BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export GIT_SHA="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
export HOST_KERNEL="$(uname -r)"
export HOST_OS="$(uname -s)"

echo "==> Build metadata"
echo "    BUILD_DATE: $BUILD_DATE"
echo "    GIT_SHA:    $GIT_SHA"
echo "    KERNEL:     $HOST_KERNEL"

# ── Create required directories ───────────────────────────────────────────────
mkdir -p "$REPO_ROOT/artifacts/logs"
mkdir -p "$REPO_ROOT/artifacts/phase3_6"
mkdir -p "$REPO_ROOT/results"

# ── Start services ────────────────────────────────────────────────────────────
echo "==> Starting Docker Compose services"
cd "$DOCKER_DIR"
docker compose up -d \
    --build \
    --remove-orphans \
    2>&1 | tee "$REPO_ROOT/artifacts/logs/testbed_start.log"

# ── Wait for health ───────────────────────────────────────────────────────────
echo "==> Waiting for services to become healthy (up to 120s)"
"$SCRIPT_DIR/health_check_testbed.sh" --wait 120 || {
    echo "ERROR: Health check failed. Check artifacts/logs/testbed_start.log" >&2
    exit 1
}

echo ""
echo "======================================================"
echo " RIFT Testbed: STARTED"
echo " Prometheus:   http://localhost:9090"
echo " Jaeger UI:    http://localhost:16686"
echo " Boutique:     http://localhost:8080"
echo " Logs:         artifacts/logs/testbed_start.log"
echo "======================================================"
echo ""
echo "Next: run ./scripts/health_check_testbed.sh"
echo "Then: make reproduce-all"
