#!/bin/bash

# Realtime Cooking Mama Server Starter
# Starts the server in background and saves PID

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/.server.pid"
LOG_FILE="$PROJECT_DIR/server.log"

cd "$PROJECT_DIR"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "❌ Server is already running (PID: $PID)"
        echo "To stop: ./scripts/stop-server.sh"
        exit 1
    else
        echo "⚠️  Removing old PID file..."
        rm -f "$PID_FILE"
    fi
fi

# Activate virtual environment and start server
echo "🚀 Starting server..."
source venv/bin/activate

# Run server in background
nohup python main.py > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

# Save PID
echo "$SERVER_PID" > "$PID_FILE"

# Wait for server to start
sleep 2

# Check if server started successfully
if ps -p "$SERVER_PID" > /dev/null 2>&1; then
    echo "✅ Server started successfully!"
    echo "   PID: $SERVER_PID"
    echo "   URL: http://localhost:5050"
    echo "   Log: tail -f $LOG_FILE"
    echo ""
    echo "To stop: ./scripts/stop-server.sh"
else
    echo "❌ Server failed to start"
    echo "Check logs: cat $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
