#!/usr/bin/env bash
# RIFT Testbed Health Check — Phase 3.6 §4
#
# Checks that all required services are healthy and responding.
# May be called standalone or from start_testbed.sh.
#
# Options:
#   --wait N    Wait up to N seconds for all services (default: 0, immediate check)
#
# Exit codes:
#   0 — All checks passed
#   1 — One or more checks failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

WAIT_S=0
if [[ "${1:-}" == "--wait" && -n "${2:-}" ]]; then
    WAIT_S="$2"
fi

OS="$(uname -s)"
if [[ "$OS" != "Linux" ]]; then
    echo "ERROR: health_check_testbed.sh requires Linux." >&2
    echo "  Detected OS: $OS" >&2
    echo "  Status: READY_FOR_LINUX" >&2
    exit 1
fi

declare -A ENDPOINTS=(
    ["Prometheus"]="http://localhost:9090/-/healthy"
    ["Jaeger_UI"]="http://localhost:16686/"
    ["Boutique_Frontend"]="http://localhost:8080/"
)

check_endpoint() {
    local name="$1"
    local url="$2"
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
    if [[ "$http_code" =~ ^(200|301|302)$ ]]; then
        echo "  [PASS] $name ($url) → HTTP $http_code"
        return 0
    else
        echo "  [FAIL] $name ($url) → HTTP $http_code"
        return 1
    fi
}

echo "==> RIFT Testbed Health Check"

ALL_PASS=true
DEADLINE=$((SECONDS + WAIT_S))

while true; do
    ALL_PASS=true
    for name in "${!ENDPOINTS[@]}"; do
        check_endpoint "$name" "${ENDPOINTS[$name]}" || ALL_PASS=false
    done

    if $ALL_PASS; then
        break
    fi

    if [[ $SECONDS -ge $DEADLINE ]]; then
        echo ""
        echo "ERROR: Health check timed out after ${WAIT_S}s." >&2
        exit 1
    fi

    echo "  Retrying in 5s... (${SECONDS}s elapsed, deadline ${WAIT_S}s)"
    sleep 5
done

echo ""
echo "======================================================"
echo " RIFT Testbed: ALL HEALTH CHECKS PASSED"
echo "======================================================"
exit 0
