# Realtime Cooking Mama (Python)

Go 서버(yori-server)를 Python으로 완벽 이식한 프로젝트입니다.

## 기술 스택

- **FastAPI**: WebSocket + 비동기 처리
- **aiortc**: WebRTC
- **Ultralytics YOLO**: 객체 감지
- **OpenAI Realtime API**: 음성 대화
- **SQLite**: 데이터베이스 (MongoDB 대체)

## 설치

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 작성:

```env
PASSWORD=your_password
OPENAI_API_KEY=sk-...
```

### 3. 리소스 파일 준비

`resources/` 디렉토리에 다음 파일들이 필요합니다:
- `yori_detector.onnx` - YOLO 모델
- `data-names.yaml` - 클래스 이름
- `recipe.json` - 레시피 데이터

## 실행

```bash
python main.py
```

서버가 `http://localhost:5050`에서 실행됩니다.

브라우저에서 `http://localhost:5050`에 접속하면 test.html이 표시됩니다.

## 프로젝트 구조

```
realtime-cooking-mama/
├── main.py                 # 메인 서버
├── requirements.txt        # 의존성
├── pytest.ini             # 테스트 설정
├── tests/                 # 테스트 코드
├── models/                # 데이터 모델
├── utils/                 # 유틸리티
├── core/                  # 핵심 로직
├── handlers/              # WebRTC 핸들러
├── resources/             # 리소스 파일
└── test.html             # 테스트 클라이언트
```

## 테스트

```bash
pytest
```

## 주요 기능

1. **WebRTC 기반 실시간 비디오/오디오 통신**
2. **YOLO 객체 감지** (식재료 인식)
3. **OpenAI Realtime API** (음성 대화)
4. **냉장고 관리**
5. **레시피 추천 및 단계별 가이드**
6. **요리 기록 저장**

## API 호환성

이 프로젝트는 Go 서버와 100% 호환됩니다. test.html이 수정 없이 동작합니다.

## 환경 변수

- `PASSWORD`: WebSocket 인증 비밀번호
- `OPENAI_API_KEY`: OpenAI API 키
- `PROFILE`: 프로파일 (local, production 등)
- `DEBUG_MODE`: 디버그 모드 (true/false)

## 라이센스

프로젝트 라이센스에 따름

