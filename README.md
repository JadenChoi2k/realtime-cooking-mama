# Realtime Cooking Mama (Python)

A complete Python port of the Go server (yori-server) with 1:1 feature parity.

## Tech Stack

- **FastAPI**: WebSocket + Async processing
- **aiortc**: WebRTC implementation
- **Ultralytics YOLO**: Object detection
- **OpenAI Realtime API**: Voice conversation
- **SQLite**: Database (replaces MongoDB)

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

**Copy resources from the Go server:**

```bash
# Assuming yori-server is at ../../../yori-server
mkdir -p resources
cp ../../../yori-server/resources/yori_detector.onnx resources/
cp ../../../yori-server/resources/data-names.yaml resources/
cp ../../../yori-server/resources/recipe.json resources/
```

Required files:

- `yori_detector.onnx` - YOLO object detection model
- `data-names.yaml` - Detection class names list
- `recipe.json` - Recipe database

**Note**: This project does NOT require `.env` files or environment variable setup!
API keys are entered directly from the client side.

## Running the Server

### Method 1: Using Scripts (Recommended)

```bash
# Start server
./scripts/start-server.sh

# Check server status
./scripts/validate-server.sh

# Stop server
./scripts/stop-server.sh
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
3. **OpenAI Realtime API** (Voice conversation)
4. **Fridge Management**
5. **Recipe Recommendation and Step-by-step Guidance**
6. **Cooking History Storage**

## Architecture

### Security Design

This project is designed with a **client-side API key input approach**:

- No need to store API keys on the server
- Each user uses their own API key
- No `.env` file configuration needed
- Optimized for local development/testing

### Differences from Original Go Server

| Feature            | Go Server                    | Python Server (This Project) |
| ------------------ | ---------------------------- | ---------------------------- |
| Authentication     | Server-side PASSWORD env var | Client-side API key input    |
| Object Detection   | GoCV or external server      | Ultralytics YOLO (built-in)  |
| Database           | MongoDB                      | SQLite                       |
| API Key Management | Server environment variable  | Client input                 |

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

**No required environment variables!** The following are optional:

- `PROFILE`: Profile (local, production, etc.) - Default: ""
- `DEBUG_MODE`: Debug mode (true/false) - Default: false

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

## License

Follows project license

## Contributors

Developed as a complete port from the Go-based yori-server to Python, maintaining full feature compatibility with test.html client.
