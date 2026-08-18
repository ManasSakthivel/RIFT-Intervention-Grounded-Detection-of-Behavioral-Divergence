#!/usr/bin/env bash
# RIFT Testbed Shutdown Script — Phase 3.6 §4
# Stops all RIFT evaluation testbed services and cleans up containers.
#
# Usage: ./scripts/stop_testbed.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_DIR="$REPO_ROOT/docker"

OS="$(uname -s)"
if [[ "$OS" != "Linux" ]]; then
    echo "ERROR: stop_testbed.sh requires Linux." >&2
    echo "  Detected OS: $OS" >&2
    echo "  Status: READY_FOR_LINUX" >&2
    exit 1
fi

echo "==> RIFT Testbed Shutdown"

cd "$DOCKER_DIR"
docker compose down \
    --remove-orphans \
    2>&1 | tee "$REPO_ROOT/artifacts/logs/testbed_stop.log"

echo ""
echo "======================================================"
echo " RIFT Testbed: STOPPED"
echo " Log: artifacts/logs/testbed_stop.log"
echo "======================================================"
