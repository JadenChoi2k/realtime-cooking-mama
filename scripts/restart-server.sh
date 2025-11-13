#!/bin/bash

# Realtime Cooking Mama Server Restarter
# Stops and restarts the server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🔄 Restarting server..."

# Stop server if running
if [ -f "$PROJECT_DIR/.server.pid" ]; then
    echo "📍 Stopping server..."
    ./scripts/stop-server.sh || true
    sleep 1
else
    echo "ℹ️  Server is not running"
fi

# Start server
echo "📍 Starting server..."
./scripts/start-server.sh

echo ""
echo "✅ Server restarted successfully!"

