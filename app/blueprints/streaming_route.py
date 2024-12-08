from flask import Blueprint
import requests
import sys
from datetime import datetime, timedelta, UTC
import pytz
import logging
from pathlib import Path
from openai import OpenAI

DATA_PATH = "/data"
CHUNK_TIME_SECONDS = 10
RECENT_FILES_TIME_MIN = 10
PATH_AUDIO_FILES = "/data/audio"

streaming_routes = Blueprint('streaming', __name__)

log = logging.getLogger(__name__)
client = OpenAI()


@streaming_routes.route("/")
def index():
    return {"message": "Streaming server is running"}

    # try:
    #     stream_to_file = requests.args.get("stream_to_file", "false")
    #     if stream_to_file == "true":
    #         record_stream_to_file(requests.stream)
    #         transcribe = transcribe_file("whisper-1", get_recent_files())
    #         return {"status": "success", "transcribe": transcribe}
    # except Exception as e:
    #     log.error(f"Error processing stream request: {str(e)}")
    #     return {"status": "error", "message": str(e)}, 500

def record_stream_to_file(stream: requests.Response):
    """Record stream audio to files as .mp3 in chunks during recording times
    Args:
        stream (requests.Response): Audio stream
    """
    start_utc = datetime.now(UTC)
    start_local = datetime.now(tz=pytz.timezone('America/New_York'))
    
    filename = DATA_PATH + "/stream_" + start_utc.isoformat(timespec="seconds") + ".mp3"
    log.info("Writing stream to: %s", filename)
    
    with open(filename, "wb") as file:
        try:
            for block in stream.iter_content(1024):
                file.write(block)
                if datetime.now(UTC) - start_utc > timedelta(
                    seconds=CHUNK_TIME_SECONDS
                ):
                    file.close()
                    record_stream_to_file(stream)
        except KeyboardInterrupt:
            log.info("Received keyboard interrupt")
            sys.exit(0)
    
def get_recent_files() -> list:
    """Return file paths for recently created files
    Returns:
        list: File paths
    """
    log.info("Listing recent files")
    now = datetime.utcnow()
    audio_files = []
    for file in sorted(Path(PATH_AUDIO_FILES).iterdir()):
        if ".mp3" in file.name:
            file_ts = datetime.fromtimestamp(file.stat().st_ctime)
            if now - file_ts <= timedelta(minutes=RECENT_FILES_TIME_MIN):
                audio_files.append(file)
    log.debug("Recent files: %s", audio_files)
    return audio_files

# Define transcription logic
def transcribe_file(model_str, file_path):
    """
    Transcribe an audio file using Whisper.
    Args:
        model: Whisper model instance
        file_path (str): Path to the audio file
    Returns:
        str: Transcription text
    """
    try:
        transcription = client.audio.transcriptions.create(
            model=model_str, 
            file=file_path
        )
        print(f"[TRANSCRIPTION] {transcription.text}")
        return transcription.text
    except Exception as e:
        print(f"[ERROR] Transcription failed for {file_path}: {e}")
        return ""
