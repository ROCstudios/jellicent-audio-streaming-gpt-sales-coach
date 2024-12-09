import React, { useState, useRef } from "react";
import axios from "axios";

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState("Idle");
  const mediaRecorderRef = useRef(null);

  const startRecording = async () => {
    setStatus("Starting...");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          // Convert Blob to File and send to the backend
          const audioFile = new File([event.data], "chunk.webm", {
            type: "audio/webm",
          });

          const formData = new FormData();
          formData.append("audio", audioFile);

          try {
            await axios.post("http://localhost:5001/upload", formData, {
              headers: { "Content-Type": "multipart/form-data" },
            });
            console.log("Audio chunk uploaded successfully");
          } catch (error) {
            console.error("Error uploading audio chunk:", error);
          }
        }
      };

      mediaRecorder.start(3000); // Capture audio in 3-second chunks
      mediaRecorderRef.current = mediaRecorder;

      setIsRecording(true);
      setStatus("Recording...");
    } catch (error) {
      console.error("Error accessing microphone:", error);
      setStatus("Error accessing microphone");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setStatus("Idle");
    }
  };

  return (
    <div>
      <h1>Audio Chunking Demo</h1>
      <button onClick={startRecording} disabled={isRecording}>
        Start Recording
      </button>
      <button onClick={stopRecording} disabled={!isRecording}>
        Stop Recording
      </button>
      <p>Status: {status}</p>
    </div>
  );
}

export default App;
