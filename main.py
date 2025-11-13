"""
Realtime Cooking Mama Server
Complete Python port of Go's main.go
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO
import os
from dotenv import load_dotenv
from handlers.rtc_assistant import RTCYoriAssistant

# Load environment variables
profile = os.getenv("PROFILE", "")
if profile == "local" or profile == "":
    load_dotenv()

# Create FastAPI app
app = FastAPI()

# Load YOLO model globally
print("Loading YOLO model...")
yolo_model = YOLO('./resources/yori_detector.onnx')
print("✅ YOLO model loaded successfully")


@app.get("/")
async def index():
    """
    Serve test.html as main page
    Equivalent to Go's main.go lines 31-33
    """
    with open("test.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.websocket("/signal")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket signaling endpoint
    Accepts OpenAI API Key from client
    """
    await websocket.accept()
    
    # Request API key
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
        
        # Start RTCYoriAssistant with API key
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

