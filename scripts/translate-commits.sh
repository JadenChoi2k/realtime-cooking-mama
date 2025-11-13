#!/bin/bash

# Git commit message translation script
# Translates all Korean commit messages to English

set -e

cd "$(dirname "$0")/.."

echo "🔄 Translating Git commit messages to English..."
echo ""

# Use git filter-branch to rewrite commit messages
git filter-branch -f --msg-filter '
    read msg
    case "$msg" in
        "chore: Git 저장소 초기화 및 .gitignore 설정")
            echo "chore: Initialize Git repository and setup .gitignore"
            ;;
        "feat: 프로젝트 초기 설정 및 의존성 정의")
            echo "feat: Initial project setup and dependencies"
            ;;
        "feat: 데이터 모델 정의 (Pydantic)")
            echo "feat: Define data models (Pydantic)"
            ;;
        "feat: 텍스트/오디오 유틸리티 함수 구현")
            echo "feat: Implement text/audio utility functions"
            ;;
        "feat: 냉장고, 레시피, DB 핸들러 구현")
            echo "feat: Implement fridge, recipe, and DB handlers"
            ;;
        "feat: AI 어시스턴트 및 객체 감지 구현")
            echo "feat: Implement AI assistant and object detection"
            ;;
        "feat: OpenAI Realtime API 통합 구현")
            echo "feat: Implement OpenAI Realtime API integration"
            ;;
        "feat: WebRTC 시그널링 및 미디어 처리 구현")
            echo "feat: Implement WebRTC signaling and media handling"
            ;;
        "feat: FastAPI 서버 및 테스트 클라이언트 추가")
            echo "feat: Add FastAPI server and test client"
            ;;
        "test: 모델 및 유틸리티 단위 테스트 추가")
            echo "test: Add unit tests for models and utilities"
            ;;
        "test: 코어 비즈니스 로직 단위 테스트 추가")
            echo "test: Add unit tests for core business logic"
            ;;
        "refactor: 클라이언트에서 OpenAI API key 입력받도록 개선")
            echo "refactor: Accept OpenAI API key from client side"
            ;;
        "docs: README 업데이트 및 프로젝트 완성")
            echo "docs: Update README and finalize project"
            ;;
        "feat: 서버 관리 스크립트 및 OpusHandler 추가")
            echo "feat: Add server management scripts and OpusHandler"
            ;;
        "chore: resources 디렉토리를 gitignore에 추가")
            echo "chore: Add resources directory to gitignore"
            ;;
        "docs: README에 스크립트 사용법 및 리소스 준비 방법 추가")
            echo "docs: Add script usage and resource preparation to README"
            ;;
        *)
            echo "$msg"
            ;;
    esac
' -- --all

echo ""
echo "✅ Commit messages translated successfully!"
echo ""
echo "⚠️  Note: Git history has been rewritten."
echo "   If you have already pushed, you'll need to force push:"
echo "   git push --force-with-lease"

