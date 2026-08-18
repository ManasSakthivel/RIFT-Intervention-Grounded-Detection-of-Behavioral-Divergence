#!/usr/bin/env bash
# RIFT Testbed Cleanup Script — Phase 3.6 §4
#
# Performs a full cleanup of the RIFT evaluation environment:
#   - Stop and remove all containers
#   - Remove Docker volumes
#   - Remove Docker networks
#   - Remove any residual tc netem rules (Linux only)
#   - Clear artifacts/logs/
#
# IMPORTANT: This removes ALL experiment artifacts in artifacts/logs/
# and Docker volumes. Run only when you want a completely clean state.
#
# Usage: ./scripts/cleanup_testbed.sh [--force]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_DIR="$REPO_ROOT/docker"

OS="$(uname -s)"
if [[ "$OS" != "Linux" ]]; then
    echo "ERROR: cleanup_testbed.sh requires Linux." >&2
    echo "  Detected OS: $OS" >&2
    echo "  Status: READY_FOR_LINUX" >&2
    exit 1
fi

FORCE="${1:-}"

if [[ "$FORCE" != "--force" ]]; then
    echo "WARNING: This will delete all Docker volumes and testbed artifacts."
    echo "  Run with --force to confirm."
    exit 1
fi

echo "==> RIFT Testbed Cleanup (--force)"

# Stop containers
cd "$DOCKER_DIR"
docker compose down --volumes --remove-orphans 2>&1 || true

# Remove any residual tc netem rules on eth0
echo "==> Removing any residual tc netem rules"
if command -v tc &>/dev/null; then
    tc qdisc del dev eth0 root 2>/dev/null && echo "  Removed eth0 root qdisc" || echo "  No root qdisc on eth0 (clean)"
fi

# Clear logs (keep artifacts/ structure)
echo "==> Clearing artifacts/logs/"
rm -f "$REPO_ROOT/artifacts/logs/"*.log 2>/dev/null || true

echo ""
echo "======================================================"
echo " RIFT Testbed: CLEANUP COMPLETE"
echo "======================================================"
