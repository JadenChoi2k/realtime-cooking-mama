# Realtime Cooking Mama (Python)

Realtime Cooking Mama is a real-time cooking assistant built with FastAPI, aiortc, Ultralytics YOLO, and the OpenAI Realtime API. It delivers end-to-end video, audio, and conversational guidance so users can show ingredients in the browser and receive step-by-step help while cooking.

## Tech Stack

- **FastAPI**: WebSocket + Async processing
- **aiortc**: WebRTC implementation
- **Ultralytics YOLO**: Object detection
- **OpenAI Realtime API**: Voice conversation
- **SQLite**: Embedded database for session history

## Installation

### 1. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Prepare Resource Files

**Add your resource files to `resources/`:**

```bash
mkdir -p resources
cp /path/to/your/yori_detector.onnx resources/
cp /path/to/your/data-names.yaml resources/
cp /path/to/your/recipe.json resources/
```

Required files:

- `yori_detector.onnx` - YOLO object detection model
- `data-names.yaml` - Detection class names list
- `recipe.json` - Recipe database

**Note**: This project does NOT require `.env` files or mandatory environment variables.
API keys are entered directly from the client side, but you can still opt-in to fine‑tune detection
and audio behavior via the optional variables listed below.

## Running the Server

### Method 1: Using Scripts (Recommended)

```bash
# Start server
./scripts/start-server.sh

# Stop server
./scripts/stop-server.sh

# Restart server
./scripts/restart-server.sh

# View server logs (real-time)
./scripts/log-server.sh

# Check server status
./scripts/validate-server.sh
```

### Method 2: Direct Execution

```bash
python main.py
```

The server will run at `http://localhost:5050`.

When you visit `http://localhost:5050` in your browser, test.html will be displayed.

**Click the "Start Audio Call" button and you'll be prompted to enter your OpenAI API key.**
Enter your API key (starts with `sk-`) to begin real-time voice conversation.

## Project Structure

```
realtime-cooking-mama/
├── main.py                 # Main server
├── requirements.txt        # Dependencies
├── pytest.ini             # Test configuration
├── scripts/               # Server management scripts
│   ├── start-server.sh    # Start server
│   ├── stop-server.sh     # Stop server
│   └── validate-server.sh # Validate server status
├── tests/                 # Test code
├── models/                # Data models
├── utils/                 # Utilities
├── core/                  # Core logic
├── handlers/              # WebRTC handlers
├── resources/             # Resource files
└── test.html             # Test client
```

## Testing

```bash
pytest
```

## Key Features

1. **WebRTC-based Real-time Video/Audio Communication**
2. **YOLO Object Detection** (Ingredient recognition)
   - **GPT Vision Fallback**: When YOLO returns no results, automatically falls back to GPT-4 Vision API
   - **Smart Throttling**: 5-second interval between GPT Vision calls to optimize API costs
3. **OpenAI Realtime API** (Voice conversation)
4. **Fridge Management**
5. **Recipe Recommendation and Step-by-step Guidance**
6. **Cooking History Storage**
7. **Tunable WebRTC audio pipeline (Opus bitrate/DTX/queue controls via env vars)**

## Architecture

### Security Design

This project is designed with a **client-side API key input approach**:

- No need to store API keys on the server
- Each user uses their own API key
- No `.env` file configuration needed
- Optimized for local development/testing

### GPT Vision Fallback

The system implements an intelligent fallback mechanism for object detection:

1. **Primary Detection**: YOLO model (`yori_detector.onnx`) attempts to detect ingredients
2. **Fallback Trigger**: If YOLO returns empty results, GPT-4 Vision API is called
3. **Throttling**: Minimum 5-second interval between GPT Vision calls to control costs
   제4. **Broader Detection**: GPT Vision can detect ingredients not in the YOLO training set
4. **Cost Optimization**:
   - Images are resized to 512x512 before sending
   - Low detail mode is used for API calls
   - Estimated cost: ~$0.01 per image, max 12 calls/minute with throttling

**Use Case**: When users show ingredients that YOLO wasn't trained on, or in poor lighting conditions, GPT Vision provides a reliable backup detection method.

### WebSocket Protocol

Message format between client and server:

```json
{
  "type": "system|assistant|user",
  "event": "api_key|transcript|...",
  "data": "..."
}
```

## Environment Variables (Optional)

**No required environment variables!** The following knobs are available if you want to tune behavior:

| Variable                      | Default | Description                                                                                                                     |
| ----------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `PROFILE`                     | `""`    | Optional profile name (`local`, `production`, …) used in `main.py` to decide whether to load `.env`.                            |
| `DEBUG_MODE`                  | `false` | Enables extra logging in the WebSocket signaling loop.                                                                          |
| `AUDIO_LOGGING`               | `true`  | Set to `false`/`0` to disable recording outbound/inbound audio chunks & WAVs under `logs/audio/`.                               |
| `YOLO_CONFIDENCE`             | `0.8`   | Confidence threshold for the Ultralytics YOLO detector. Increase to filter out weak detections, decrease to be more permissive. |
| `AUDIO_OPUS_BITRATE`          | `64000` | Target bitrate (bits/sec) for the server→browser Opus encoder.                                                                  |
| `AUDIO_OPUS_COMPLEXITY`       | `10`    | Opus encoder complexity (0–10). Lower values reduce CPU usage at the cost of quality.                                           |
| `AUDIO_OPUS_DTX`              | `false` | Enable Opus discontinuous transmission for silence suppression.                                                                 |
| `AUDIO_OPUS_QUEUE_MAX`        | `200`   | Maximum number of Opus frames buffered before older frames are dropped.                                                         |
| `AUDIO_SEND_METRICS_INTERVAL` | `100`   | How often the server prints/send-loop stats (in frames).                                                                        |

## Development

This project follows Test-Driven Development (TDD) principles. All core functionality is tested with pytest.

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_models.py
```

### Server Management

The `scripts/` directory contains helpful shell scripts for server management:

- `start-server.sh`: Starts the server in the background and saves the PID
- `stop-server.sh`: Gracefully stops the running server
- `restart-server.sh`: Restarts the server (stop + start)
- `log-server.sh`: Shows server logs in real-time (tail -f)
- `validate-server.sh`: Checks server status, memory usage, and resource files

## WebRTC Flow

1. Client connects via WebSocket to `/signal`
2. Server requests OpenAI API key
3. Client sends offer (SDP)
4. Server creates PeerConnection and sends answer
5. ICE candidates are exchanged
6. Media tracks (audio/video) are established
7. Real-time communication begins

## API Key Security

**Important**: This implementation is designed for local development/testing.

- The API key is transmitted over WebSocket during connection setup
- For production deployment, ensure you use WSS (WebSocket Secure) over HTTPS
- The client-side approach allows each developer to use their own API key without server configuration

## Model Training

The YOLO object detection model (`yori_detector.onnx`) was trained using:

- Custom collected and labeled ingredient data
- [COCO dataset](http://cocodataset.org) for base object detection
  - License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
  - Citation: Lin, T.-Y., et al. "Microsoft COCO: Common Objects in Context." ECCV 2014.

## Acknowledgments

This project uses the COCO dataset for object detection training. We thank the COCO dataset team for providing this valuable resource.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributors

Created and maintained by the Realtime Cooking Mama team.
