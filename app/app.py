from flask import Flask
from flask_socketio import SocketIO
from app.blueprints import streaming_route
from flask_cors import CORS

def init_app():
  app = Flask(__name__)
  CORS(app, resources={
     r"/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
  })
  socketio = SocketIO(app, cors_allowed_origins="http://localhost:3000")
  app.register_blueprint(streaming_route, url_prefix="/streaming")

  return app, socketio

if __name__ == "__main__":
  app, socketio = init_app()
  socketio.run(app, host="0.0.0.0", port=5000, debug=True)
