#!/bin/bash

# Realtime Cooking Mama Server Stopper
# Stops the running server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/.server.pid"

cd "$PROJECT_DIR"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "❌ Server is not running"
    exit 1
fi

PID=$(cat "$PID_FILE")

# Check if process is running
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  Server process does not exist (PID: $PID)"
    rm -f "$PID_FILE"
    exit 1
fi

# Stop server
echo "🛑 Stopping server... (PID: $PID)"
kill "$PID"

# Wait for process to terminate (max 10 seconds)
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Force kill if necessary
if ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  Force killing..."
    kill -9 "$PID" 2>/dev/null || true
    sleep 1
fi

# Remove PID file
rm -f "$PID_FILE"

echo "✅ Server stopped successfully"
