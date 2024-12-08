from flask import Flask
from flask_socketio import SocketIO
from blueprints.streaming_route import streaming_routes
from flask_cors import CORS

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
    print(f"[INFO] Received audio chunk: {len(audio_data)} bytes")
    print(f"[DEBUG] Type of audio_data: {type(audio_data)}")

@socketio.on("test")
def handle_test(message):
    print(f"[INFO] Test message received: {message}")

if __name__ == "__main__":
  app, socketio = init_app()
  socketio.run(app, host="0.0.0.0", port=5001, debug=True, allow_unsafe_werkzeug=True )
