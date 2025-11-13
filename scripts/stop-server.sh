#!/bin/bash

# Realtime Cooking Mama Server Stopper
# 실행 중인 서버를 중지합니다

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/.server.pid"

cd "$PROJECT_DIR"

# PID 파일이 있는지 확인
if [ ! -f "$PID_FILE" ]; then
    echo "❌ 서버가 실행 중이지 않습니다"
    exit 1
fi

PID=$(cat "$PID_FILE")

# 프로세스가 실행 중인지 확인
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  서버 프로세스가 존재하지 않습니다 (PID: $PID)"
    rm -f "$PID_FILE"
    exit 1
fi

# 서버 중지
echo "🛑 서버 중지 중... (PID: $PID)"
kill "$PID"

# 프로세스가 종료될 때까지 대기 (최대 10초)
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

# 강제 종료가 필요한 경우
if ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  강제 종료 중..."
    kill -9 "$PID" 2>/dev/null || true
    sleep 1
fi

# PID 파일 제거
rm -f "$PID_FILE"

echo "✅ 서버가 성공적으로 중지되었습니다"

