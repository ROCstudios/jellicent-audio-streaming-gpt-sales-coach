from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
import ffmpeg

app = Flask(__name__)
CORS(app)

# Directory to save uploaded audio files
SAVE_DIR = "uploaded_audio"
os.makedirs(SAVE_DIR, exist_ok=True)

def convert_to_mp3(input_path, output_path):
    """
    Convert a .webm audio file to .mp3 using ffmpeg-python.
    Args:
        input_path (str): Path to the input .webm file.
        output_path (str): Path to save the converted .mp3 file.
    """
    try:
        # Use ffmpeg to convert .webm to .mp3
        ffmpeg.input(input_path).output(output_path, format='mp3').run(quiet=True)
        print(f"[INFO] Converted {input_path} to {output_path}")
    except Exception as e:
        print(f"[ERROR] Failed to convert {input_path} to MP3: {e}")

@app.route("/upload", methods=["POST"])
def upload_audio():
    """
    Endpoint to receive audio chunks and save them as MP3 files.
    """
    try:
        audio_file = request.files["audio"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        raw_path = os.path.join(SAVE_DIR, f"chunk_{timestamp}.webm")
        mp3_path = os.path.join(SAVE_DIR, f"chunk_{timestamp}.mp3")

        # Save the raw file
        audio_file.save(raw_path)

        # Convert the file to MP3
        convert_to_mp3(raw_path, mp3_path)

        return jsonify({"message": "Audio chunk uploaded successfully", "path": mp3_path}), 200
    except Exception as e:
        print(f"[ERROR] Failed to process audio chunk: {e}")
        return jsonify({"message": "Failed to upload audio chunk"}), 500

@app.route("/")
def index():
    return jsonify({"message": "Audio backend is running"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
