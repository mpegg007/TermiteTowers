#!/usr/bin/env bash
# Run the Water Meter web viewer (FastAPI + uvicorn)
# Usage: ./run.sh [port] [host]
# Default port: 3414
# Default host: localhost

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-3414}"
HOST="${2:-localhost}"

cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "No .venv found — set it up with:"
    echo "  python3 -m venv .venv"
    echo "  .venv/bin/pip install -e ."
    exit 1
fi

echo "Starting Water Meter webapp on http://${HOST}:${PORT}"
exec .venv/bin/uvicorn water_meter.webapp.main:app \
    --app-dir src \
    --host "$HOST" \
    --port "$PORT" \
    --log-level info \
    --no-access-log
