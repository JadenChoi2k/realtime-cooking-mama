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
    Go의 signalRTCWithWebSocket 완벽 복제
    """
    await websocket.accept()
    
    # 비밀번호 인증
    await websocket.send_json({
        "type": "system",
        "event": "password",
        "data": "Please enter your password"
    })
    
    try:
        password_req = await websocket.receive_json()
        password = password_req.get("password")
        
        if password != os.getenv("PASSWORD"):
            print("Invalid password")
            await websocket.send_json({
                "type": "system",
                "event": "error",
                "data": "Invalid password"
            })
            await websocket.close()
            return
        
        # RTCYoriAssistant 시작
        assistant = RTCYoriAssistant(websocket, yolo_model)
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

