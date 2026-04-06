import { useEffect, useRef, useState } from "react";
import socket from "./socket/candidateSocket";

export default function MicrophoneSender({ sessionId }) {
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);

  // REGISTER ROLE ON MOUNT
  useEffect(() => {
    console.log(`🔐 Registering as CANDIDATE for session ${sessionId}`);
    
    socket.emit("register_role", {
      session_id: sessionId,
      role: "candidate"
    });

    socket.emit("join_session", {
      session_id: sessionId,
      role: "candidate"
    });
  }, [sessionId]);

  useEffect(() => {
    const startMic = async () => {
      try {
        console.log("🎤 Requesting microphone access...");

        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            sampleRate: 16000,
          },
        });

        console.log("✅ Microphone access granted");
        streamRef.current = stream;

        // Choose best format
        let mimeType = "audio/webm;codecs=opus";
        
        const formats = [
          "audio/webm;codecs=pcm",
          "audio/webm;codecs=opus",
          "audio/webm",
        ];

        for (const format of formats) {
          if (MediaRecorder.isTypeSupported(format)) {
            mimeType = format;
            console.log(`✅ Using audio format: ${format}`);
            break;
          }
        }

        const mediaRecorder = new MediaRecorder(stream, {
          mimeType: mimeType,
          audioBitsPerSecond: 16000,
        });

        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = async (event) => {
          if (event.data && event.data.size > 0) {
            console.log(`🔊 Audio chunk: ${event.data.size} bytes`);

            try {
              const reader = new FileReader();
              reader.onloadend = () => {
                const base64Audio = reader.result;
                console.log(`📤 Sending to backend (${base64Audio.length} chars)`);
                
                socket.emit("audio_chunk", {
                  session_id: sessionId,
                  audio: base64Audio,
                });
              };
              reader.readAsDataURL(event.data);
            } catch (err) {
              console.error("❌ Audio processing error:", err);
            }
          }
        };

        mediaRecorder.onstart = () => {
          console.log("▶️ Recording started");
          setIsRecording(true);
        };

        mediaRecorder.onstop = () => {
          console.log("⏹️ Recording stopped");
          setIsRecording(false);
        };

        mediaRecorder.onerror = (event) => {
          console.error("❌ MediaRecorder error:", event.error);
          setError(`Recording error: ${event.error.name}`);
        };

        // Start recording - 2 second chunks
        mediaRecorder.start(2000);
        console.log("🎙️ MediaRecorder started");

      } catch (err) {
        console.error("❌ Microphone error:", err);
        
        if (err.name === "NotAllowedError") {
          setError("Microphone access denied");
        } else {
          setError(`Microphone error: ${err.message}`);
        }
      }
    };

    startMic();

    return () => {
      console.log("🧹 Cleaning up microphone");

      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }

      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, [sessionId]);

  return (
    <div style={{ display: "none" }}>
      {error && console.error("Mic Error:", error)}
    </div>
  );
}