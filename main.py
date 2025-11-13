"""
Realtime Cooking Mama Server
Go의 main.go 완벽 복제 (Python 버전)
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO
import os
from dotenv import load_dotenv
from handlers.rtc_assistant import RTCYoriAssistant

# 환경 변수 로드
profile = os.getenv("PROFILE", "")
if profile == "local" or profile == "":
    load_dotenv()

# FastAPI 앱 생성
app = FastAPI()

# YOLO 모델 글로벌 로드
print("Loading YOLO model...")
yolo_model = YOLO('./resources/yori_detector.onnx')
print("✅ YOLO model loaded successfully")


@app.get("/")
async def index():
    """
    메인 페이지 (test.html 제공)
    Go의 main.go 31-33번 라인과 동일
    """
    with open("test.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.websocket("/signal")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 시그널링 엔드포인트
    클라이언트로부터 OpenAI API Key를 받음
    """
    await websocket.accept()
    
    # API 키 요청
    await websocket.send_json({
        "type": "system",
        "event": "api_key",
        "data": "Please enter your OpenAI API Key"
    })
    
    try:
        auth_req = await websocket.receive_json()
        api_key = auth_req.get("api_key")
        
        if not api_key or not api_key.startswith("sk-"):
            print("Invalid API key")
            await websocket.send_json({
                "type": "system",
                "event": "error",
                "data": "Invalid API key"
            })
            await websocket.close()
            return
        
        # RTCYoriAssistant 시작 (API 키 전달)
        assistant = RTCYoriAssistant(websocket, yolo_model, api_key)
        await assistant.start()
        
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if 'assistant' in locals():
            await assistant.cleanup()


if __name__ == "__main__":
    import uvicorn
    
    print("Server started at :5050")
    uvicorn.run(app, host="0.0.0.0", port=5050)

