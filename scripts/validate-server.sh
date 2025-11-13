#!/bin/bash

# Realtime Cooking Mama Server Validator
# Checks and validates server status

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/.server.pid"
SERVER_URL="http://localhost:5050"

cd "$PROJECT_DIR"

echo "🔍 Validating server..."
echo ""

# 1. Check PID file
if [ ! -f "$PID_FILE" ]; then
    echo "❌ Server is not running (PID file not found)"
    echo "   To start: ./scripts/start-server.sh"
    exit 1
fi

PID=$(cat "$PID_FILE")
echo "✅ PID file exists: $PID"

# 2. Check process
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "❌ Server process is not running"
    rm -f "$PID_FILE"
    exit 1
fi
echo "✅ Process running: PID $PID"

# 3. Check memory usage
MEM_INFO=$(ps -o rss= -p "$PID" | awk '{print $1/1024 " MB"}')
echo "✅ Memory usage: $MEM_INFO"

# 4. Check HTTP endpoint
if command -v curl &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL" || echo "000")
    if [ "$HTTP_CODE" == "200" ]; then
        echo "✅ HTTP endpoint responding: $SERVER_URL (200 OK)"
    else
        echo "⚠️  HTTP endpoint response code: $HTTP_CODE"
        if [ "$HTTP_CODE" == "000" ]; then
            echo "   (Server may still be starting)"
        fi
    fi
else
    echo "⚠️  curl not installed, skipping HTTP check"
fi

# 5. Check resource files
echo ""
echo "📁 Resource files check:"
RESOURCES_OK=true

if [ -f "$PROJECT_DIR/resources/yori_detector.onnx" ]; then
    echo "✅ YOLO model: resources/yori_detector.onnx"
else
    echo "❌ YOLO model missing: resources/yori_detector.onnx"
    RESOURCES_OK=false
fi

if [ -f "$PROJECT_DIR/resources/data-names.yaml" ]; then
    echo "✅ Class names: resources/data-names.yaml"
else
    echo "❌ Class names missing: resources/data-names.yaml"
    RESOURCES_OK=false
fi

if [ -f "$PROJECT_DIR/resources/recipe.json" ]; then
    echo "✅ Recipe data: resources/recipe.json"
else
    echo "❌ Recipe data missing: resources/recipe.json"
    RESOURCES_OK=false
fi

# 6. Check virtual environment
echo ""
if [ -d "$PROJECT_DIR/venv" ]; then
    echo "✅ Virtual environment: venv/"
else
    echo "⚠️  Virtual environment not found"
fi

# Final result
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$RESOURCES_OK" == "true" ]; then
    echo "✅ Server is running normally!"
    echo "   URL: $SERVER_URL"
    echo "   Log: tail -f $PROJECT_DIR/server.log"
else
    echo "⚠️  Server is running but some resource files are missing"
    echo "   Object detection and recipe features may not work"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
