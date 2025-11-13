#!/bin/bash

# Realtime Cooking Mama Server Validator
# 서버 상태를 확인하고 검증합니다

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/.server.pid"
SERVER_URL="http://localhost:5050"

cd "$PROJECT_DIR"

echo "🔍 서버 검증 중..."
echo ""

# 1. PID 파일 확인
if [ ! -f "$PID_FILE" ]; then
    echo "❌ 서버가 실행 중이지 않습니다 (PID 파일 없음)"
    echo "   시작하려면: ./scripts/start-server.sh"
    exit 1
fi

PID=$(cat "$PID_FILE")
echo "✅ PID 파일 존재: $PID"

# 2. 프로세스 확인
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "❌ 서버 프로세스가 실행 중이지 않습니다"
    rm -f "$PID_FILE"
    exit 1
fi
echo "✅ 프로세스 실행 중: PID $PID"

# 3. 메모리 사용량 확인
MEM_INFO=$(ps -o rss= -p "$PID" | awk '{print $1/1024 " MB"}')
echo "✅ 메모리 사용량: $MEM_INFO"

# 4. HTTP 엔드포인트 확인
if command -v curl &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL" || echo "000")
    if [ "$HTTP_CODE" == "200" ]; then
        echo "✅ HTTP 엔드포인트 응답: $SERVER_URL (200 OK)"
    else
        echo "⚠️  HTTP 엔드포인트 응답 코드: $HTTP_CODE"
        if [ "$HTTP_CODE" == "000" ]; then
            echo "   (서버가 아직 시작 중일 수 있습니다)"
        fi
    fi
else
    echo "⚠️  curl이 설치되지 않아 HTTP 체크를 건너뜁니다"
fi

# 5. 리소스 파일 확인
echo ""
echo "📁 리소스 파일 확인:"
RESOURCES_OK=true

if [ -f "$PROJECT_DIR/resources/yori_detector.onnx" ]; then
    echo "✅ YOLO 모델: resources/yori_detector.onnx"
else
    echo "❌ YOLO 모델 없음: resources/yori_detector.onnx"
    RESOURCES_OK=false
fi

if [ -f "$PROJECT_DIR/resources/data-names.yaml" ]; then
    echo "✅ 클래스 이름: resources/data-names.yaml"
else
    echo "❌ 클래스 이름 없음: resources/data-names.yaml"
    RESOURCES_OK=false
fi

if [ -f "$PROJECT_DIR/resources/recipe.json" ]; then
    echo "✅ 레시피 데이터: resources/recipe.json"
else
    echo "❌ 레시피 데이터 없음: resources/recipe.json"
    RESOURCES_OK=false
fi

# 6. 가상 환경 확인
echo ""
if [ -d "$PROJECT_DIR/venv" ]; then
    echo "✅ 가상 환경: venv/"
else
    echo "⚠️  가상 환경이 없습니다"
fi

# 최종 결과
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$RESOURCES_OK" == "true" ]; then
    echo "✅ 서버가 정상적으로 실행 중입니다!"
    echo "   URL: $SERVER_URL"
    echo "   로그: tail -f $PROJECT_DIR/server.log"
else
    echo "⚠️  서버는 실행 중이지만 일부 리소스 파일이 없습니다"
    echo "   객체 감지 및 레시피 기능이 작동하지 않을 수 있습니다"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

