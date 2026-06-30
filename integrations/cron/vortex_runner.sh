#!/bin/bash
# VORTEX cron runner — runs optimization cycle for a project
# Usage: vortex_runner.sh <manifest_path>

set -euo pipefail

MANIFEST="${1:?Usage: vortex_runner.sh <manifest_path>}"
VORTEX_DIR="/home/jul/projects/vortex"

cd "$VORTEX_DIR"
source .venv/bin/activate

echo "[$(date -Iseconds)] VORTEX: Starting cycle for $MANIFEST"
vortex run "$MANIFEST" --cycle 2>&1
echo "[$(date -Iseconds)] VORTEX: Cycle complete"
