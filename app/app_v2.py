from flask import Flask
from flask_socketio import SocketIO
from blueprints.streaming_route import streaming_routes
from flask_cors import CORS
from datetime import datetime
import os
from datetime import datetime, timedelta, UTC
from pydub import AudioSegment
import io

SAVE_DIR="./data"
os.makedirs(SAVE_DIR, exist_ok=True)

CHUNK_TIME_SECONDS = 10
CHANNELS = 1  # or 2 if stereo
SAMPLE_WIDTH = 2  # typically 16-bit audio
FRAME_RATE = 44100  # standard audio rate

current_buffer = bytearray()
last_save_time = datetime.now(UTC) 

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

def init_app():
  CORS(app, resources={
     r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
  })
  app.register_blueprint(streaming_routes, url_prefix="/streaming")

  return app, socketio

# @socketio.on("audio_stream")
# def handle_audio_stream(audio_data):
#     print(f"[INFO] Received audio chunk: {len(audio_data)} bytes")

@app.route("/")
def index():
    return {"message": "WebSocket server is running"}

@socketio.on("connect")
def handle_connect():
    print("[INFO] Client connected")

@socketio.on("disconnect")
def handle_disconnect():
    print("[INFO] Client disconnected")

@socketio.on("audio_stream")
def handle_audio_stream(audio_data):
    """
    Handle audio stream from client and saves to mp3 directory
    """
    global current_buffer, last_save_time
    
    try:
        # Debug incoming data
        print(f"[DEBUG] Received chunk size: {len(audio_data)} bytes")
        print(f"[DEBUG] Audio data type: {type(audio_data)}")
        if isinstance(audio_data, bytes):
            print(f"[DEBUG] First few bytes: {audio_data[:10].hex()}")
        
        # Convert incoming data to bytes if needed
        if isinstance(audio_data, (list, tuple)):
            audio_bytes = bytes(audio_data)
        elif not isinstance(audio_data, bytes):
            audio_bytes = bytes([audio_data])
        else:
            audio_bytes = audio_data

        # Debug converted data
        print(f"[DEBUG] Converted chunk size: {len(audio_bytes)} bytes")
        print(f"[DEBUG] Buffer size before append: {len(current_buffer)} bytes")

        # Add to buffer
        current_buffer.extend(audio_bytes)
        print(f"[DEBUG] Buffer size after append: {len(current_buffer)} bytes")
        
        # Check if it's time to save
        current_time = datetime.now(UTC)
        time_diff = (current_time - last_save_time).total_seconds()
        print(f"[DEBUG] Time since last save: {time_diff} seconds")

        if time_diff >= CHUNK_TIME_SECONDS:
            timestamp = current_time.strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(SAVE_DIR, f"chunk_{timestamp}.mp3")
            
            # Convert raw audio to MP3
            raw_audio = AudioSegment(
                data=bytes(current_buffer),
                sample_width=SAMPLE_WIDTH,
                frame_rate=FRAME_RATE,
                channels=CHANNELS
            )
            
            # Export as MP3
            raw_audio.export(file_path, format="mp3")
            print(f"[INFO] Successfully saved MP3 file: {file_path}")
            
            current_buffer.clear()
            last_save_time = current_time
            print("[DEBUG] Buffer cleared and timestamp updated")
        
    except Exception as e:
        print(f"[ERROR] Failed to save audio chunk: {str(e)}")
        print(f"[ERROR] Error type: {type(e).__name__}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

@socketio.on("test")
def handle_test(message):
    print(f"[INFO] Test message received: {message}")

if __name__ == "__main__":
  app, socketio = init_app()
  socketio.run(app, host="0.0.0.0", port=5001, debug=True, allow_unsafe_werkzeug=True )
