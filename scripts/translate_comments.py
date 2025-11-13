#!/usr/bin/env python3
"""
Translate Korean comments and docstrings to English in Python files
"""
import os
import re
from pathlib import Path

# Translation dictionary for common patterns
TRANSLATIONS = {
    # File headers
    "오디오 유틸리티": "Audio Utilities",
    "텍스트 유틸리티": "Text Utilities",
    "데이터 모델": "Data Models",
    "이벤트 모델": "Event Models",
    "레시피 모델": "Recipe Models",
    "요리 기록 모델": "Cooking Record Model",
    "냉장고 관리": "Fridge Management",
    "레시피 관리": "Recipe Management",
    "데이터베이스 핸들러": "Database Handler",
    "객체 감지": "Object Detection",
    "비디오 객체 감지": "Video Object Detection",
    "OpenAI 어시스턴트": "OpenAI Assistant",
    "실시간 AI 어시스턴트": "Realtime AI Assistant",
    "WebRTC 핸들러": "WebRTC Handler",
    
    # Common patterns
    "Go의 (.+?) 완벽 복제": r"Complete port of Go's \1",
    "Go의 (.+?) 구조체와 동일": r"Equivalent to Go's \1 struct",
    "Go의 (.+?) 함수와 동일": r"Same as Go's \1 function",
    
    # Function/class descriptions
    "초기화": "Initialize",
    "시작": "Start",
    "중지": "Stop",
    "종료": "Cleanup",
    "처리": "Handle",
    "관리": "Manage",
    "검증": "Validate",
    "생성": "Create",
    "업데이트": "Update",
    "삭제": "Delete",
    "조회": "Get/Retrieve",
    "추가": "Add",
    "제거": "Remove",
    "변환": "Convert",
    "인코딩": "Encode",
    "디코딩": "Decode",
    
    # Data types
    "바이트 배열": "byte array",
    "리스트": "list",
    "문자열": "string",
    "정수": "integer",
    "딕셔너리": "dictionary",
    
    # Common phrases
    "다음": "next",
    "이전": "previous",
    "완료": "complete",
    "성공": "success",
    "실패": "failure",
    "오류": "error",
    "경고": "warning",
    "정보": "info",
    
    # Args/Returns
    "매개변수": "Args",
    "반환값": "Returns",
    "반환": "Returns",
    "인자": "Args",
    
    # Specific translations
    "환경 변수 로드": "Load environment variables",
    "FastAPI 앱 생성": "Create FastAPI app",
    "YOLO 모델 글로벌 로드": "Load YOLO model globally",
    "메인 페이지": "Main page",
    "WebSocket 시그널링 엔드포인트": "WebSocket signaling endpoint",
    "클라이언트로부터 OpenAI API Key를 받음": "Accepts OpenAI API Key from client",
    "API 키 요청": "Request API key",
    "RTCYoriAssistant 시작": "Start RTCYoriAssistant",
    
    # Ingredient/Recipe related
    "식재료 정보": "Ingredient information",
    "레시피에 사용되는 식재료와 수량": "Ingredient with quantity used in recipe",
    "레시피 단계": "Recipe step information",
    "레시피 정보": "Recipe information",
    "요리 완료 기록": "Cooking completion record",
    
    # Random string
    "랜덤 문자열 생성": "Generate random string",
    "생성할 문자열 길이": "Length of string to generate",
    "랜덤 알파벳 문자열": "Random alphabetic string",
    
    # Audio utils
    "바이트 배열을 int16 리스트로 변환": "Convert byte array to int16 list",
    "int16 리스트를 바이트 배열로 변환": "Convert int16 list to byte array",
    "PCM 데이터 리샘플링": "Resample PCM data",
    "선형 보간": "Linear interpolation",
    "2채널 PCM을 1채널로 변환": "Convert 2-channel PCM to 1-channel",
    "왼쪽 채널만 추출": "Extract left channel only",
    "채널 수 증가": "Increase channel count",
    "각 샘플 복제": "Replicate each sample",
    "PCM16 데이터를 base64로 인코딩": "Encode PCM16 data to base64",
    "청크 단위 처리": "chunk-wise processing",
    "Opus 코덱 핸들러": "Opus codec handler",
    "Opus 데이터를 PCM16으로 디코딩": "Decode Opus data to PCM16",
    "PCM16 데이터를 Opus로 인코딩": "Encode PCM16 data to Opus",
    "샘플레이트": "sample rate",
    "채널 수": "number of channels",
    "프레임 크기 계산": "Calculate frame size",
    
    # More specific terms
    "입력 PCM 데이터": "input PCM data",
    "출력 PCM 데이터": "output PCM data",
    "원본 샘플레이트": "source sample rate",
    "목표 샘플레이트": "target sample rate",
    "리샘플링된 PCM 데이터": "resampled PCM data",
    "원본 채널 수": "source channel count",
    "목표 채널 수": "target channel count",
    "증가된 채널의 PCM 데이터": "PCM data with increased channels",
    "PCM 바이트 데이터": "PCM byte data",
    "base64 인코딩된 문자열": "base64 encoded string",
    "Opus 인코딩된 데이터": "Opus encoded data",
    "모노": "mono",
    "스테레오": "stereo",
    "예": "e.g.",
    "마지막 인덱스": "last index",
    "범위 초과": "out of range",
}

def translate_text(text):
    """Translate Korean text to English using pattern matching"""
    result = text
    
    # Apply regex patterns first
    for korean, english in TRANSLATIONS.items():
        if r"\1" in english:  # regex pattern
            result = re.sub(korean, english, result)
    
    # Then apply direct replacements
    for korean, english in TRANSLATIONS.items():
        if r"\1" not in english:  # not a regex pattern
            result = result.replace(korean, english)
    
    return result

def process_file(filepath):
    """Process a single Python file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if file has Korean characters
    if not re.search('[ㄱ-ㅎㅏ-ㅣ가-힣]', content):
        return False
    
    # Translate content
    translated = translate_text(content)
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(translated)
    
    return True

def main():
    """Main function to process all Python files"""
    project_root = Path(__file__).parent.parent
    
    # Directories to process
    dirs_to_process = ['models', 'utils', 'core', 'handlers', 'tests']
    
    # Also process root files
    root_files = ['main.py']
    
    processed_count = 0
    total_count = 0
    
    print("🔄 Translating Korean comments to English...")
    print()
    
    # Process root files
    for filename in root_files:
        filepath = project_root / filename
        if filepath.exists():
            total_count += 1
            if process_file(filepath):
                print(f"✅ {filename}")
                processed_count += 1
    
    # Process directories
    for dir_name in dirs_to_process:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            continue
        
        for py_file in dir_path.glob('*.py'):
            if py_file.name.startswith('__'):
                continue
            
            total_count += 1
            if process_file(py_file):
                print(f"✅ {dir_name}/{py_file.name}")
                processed_count += 1
    
    print()
    print(f"✅ Translation complete!")
    print(f"   Processed: {processed_count}/{total_count} files")

if __name__ == '__main__':
    main()

