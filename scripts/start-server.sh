#!/bin/bash

# Realtime Cooking Mama Server Starter
# 서버를 백그라운드에서 실행하고 PID를 저장합니다

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/.server.pid"
LOG_FILE="$PROJECT_DIR/server.log"

cd "$PROJECT_DIR"

# 이미 실행 중인지 확인
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "❌ 서버가 이미 실행 중입니다 (PID: $PID)"
        echo "중지하려면: ./scripts/stop-server.sh"
        exit 1
    else
        echo "⚠️  이전 PID 파일 제거 중..."
        rm -f "$PID_FILE"
    fi
fi

# 가상 환경 활성화 및 서버 시작
echo "🚀 서버 시작 중..."
source venv/bin/activate

# 백그라운드에서 서버 실행
nohup python main.py > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

# PID 저장
echo "$SERVER_PID" > "$PID_FILE"

# 서버 시작 대기
sleep 2

# 서버가 정상적으로 시작되었는지 확인
if ps -p "$SERVER_PID" > /dev/null 2>&1; then
    echo "✅ 서버가 성공적으로 시작되었습니다!"
    echo "   PID: $SERVER_PID"
    echo "   URL: http://localhost:5050"
    echo "   로그: tail -f $LOG_FILE"
    echo ""
    echo "중지하려면: ./scripts/stop-server.sh"
else
    echo "❌ 서버 시작 실패"
    echo "로그를 확인하세요: cat $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi

