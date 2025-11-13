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

### 2. 리소스 파일 준비

`resources/` 디렉토리에 다음 파일들이 필요합니다:
- `yori_detector.onnx` - YOLO 모델
- `data-names.yaml` - 클래스 이름
- `recipe.json` - 레시피 데이터

**참고**: 이 프로젝트는 `.env` 파일이나 환경 변수 설정이 필요 없습니다! 
클라이언트에서 직접 OpenAI API 키를 입력받습니다.

## 실행

```bash
python main.py
```

서버가 `http://localhost:5050`에서 실행됩니다.

브라우저에서 `http://localhost:5050`에 접속하면 test.html이 표시됩니다.

**"Start Audio Call" 버튼을 클릭하면 OpenAI API 키를 입력하는 프롬프트가 나타납니다.**
자신의 API 키(`sk-`로 시작)를 입력하면 실시간 음성 대화가 시작됩니다.

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

## 아키텍처

### 보안 설계

이 프로젝트는 **클라이언트 사이드에서 API 키를 입력받는 방식**으로 설계되어:
- 서버에 API 키를 저장할 필요가 없음
- 각 사용자가 자신의 API 키 사용
- `.env` 파일 설정 불필요
- 로컬 개발/테스트에 최적화

### 원본 Go 서버와의 차이점

| 항목 | Go 서버 | Python 서버 (이 프로젝트) |
|------|---------|--------------------------|
| 인증 방식 | 서버의 PASSWORD 환경 변수 | 클라이언트에서 API key 입력 |
| 객체 감지 | GoCV 또는 외부 서버 | Ultralytics YOLO (내장) |
| 데이터베이스 | MongoDB | SQLite |
| API 키 관리 | 서버 환경 변수 | 클라이언트 입력 |

### WebSocket 프로토콜

클라이언트와 서버 간 메시지 형식:

```json
{
  "type": "system|assistant|user",
  "event": "api_key|transcript|...",
  "data": "..."
}
```

## 환경 변수 (선택 사항)

**필수 환경 변수는 없습니다!** 다음은 선택적으로 사용 가능:

- `PROFILE`: 프로파일 (local, production 등) - 기본값: ""
- `DEBUG_MODE`: 디버그 모드 (true/false) - 기본값: false

## 라이센스

프로젝트 라이센스에 따름

