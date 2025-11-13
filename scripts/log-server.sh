#!/bin/bash

# Realtime Cooking Mama Server Logger
# Shows server logs in real-time

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/server.log"

cd "$PROJECT_DIR"

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Log file not found: $LOG_FILE"
    echo ""
    echo "The server may not have been started yet."
    echo "To start: ./scripts/start-server.sh"
    exit 1
fi

# Check if server is running
if [ -f "$PROJECT_DIR/.server.pid" ]; then
    PID=$(cat "$PROJECT_DIR/.server.pid")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "📊 Server is running (PID: $PID)"
    else
        echo "⚠️  Server is not running (stale log file)"
    fi
else
    echo "⚠️  Server is not running (viewing old logs)"
fi

echo "📝 Showing logs from: $LOG_FILE"
echo "   Press Ctrl+C to exit"
echo ""
echo "----------------------------------------"

# Follow log file
tail -f "$LOG_FILE"

