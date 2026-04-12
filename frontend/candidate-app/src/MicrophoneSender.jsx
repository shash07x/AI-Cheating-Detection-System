import { useEffect, useRef, useState } from "react";
import socket from "./socket/candidateSocket";

/**
 * MicrophoneSender — Captures microphone audio and sends raw PCM float32
 * to the backend every 2 seconds via WebSocket.
 *
 * Uses Web Audio API (ScriptProcessorNode) instead of MediaRecorder to
 * avoid WebM fragmentation issues where only the first chunk is decodable.
 * Sends raw base64-encoded float32 PCM at 16kHz mono.
 */
export default function MicrophoneSender({ sessionId }) {
  const streamRef = useRef(null);
  const audioCtxRef = useRef(null);
  const processorRef = useRef(null);
  const bufferRef = useRef([]);
  const intervalRef = useRef(null);
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
            channelCount: 1,
            sampleRate: 16000,
          },
        });

        console.log("✅ Microphone access granted");
        streamRef.current = stream;

        // Create audio context at 16kHz for direct PCM capture
        const audioContext = new (window.AudioContext || window.webkitAudioContext)({
          sampleRate: 16000,
        });
        audioCtxRef.current = audioContext;

        const source = audioContext.createMediaStreamSource(stream);

        // ScriptProcessorNode captures raw PCM float32 samples
        // Buffer size 4096 at 16kHz = ~256ms per callback
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (e) => {
          const inputData = e.inputBuffer.getChannelData(0);
          // Copy the float32 samples into our buffer
          bufferRef.current.push(new Float32Array(inputData));
        };

        source.connect(processor);
        processor.connect(audioContext.destination);

        console.log(`✅ Audio capture started at ${audioContext.sampleRate}Hz`);

        // Send buffered audio every 2 seconds
        intervalRef.current = setInterval(() => {
          const chunks = bufferRef.current;
          bufferRef.current = [];

          if (chunks.length === 0) return;

          // Concatenate all chunks into one Float32Array
          const totalLength = chunks.reduce((sum, c) => sum + c.length, 0);
          const combined = new Float32Array(totalLength);
          let offset = 0;
          for (const chunk of chunks) {
            combined.set(chunk, offset);
            offset += chunk.length;
          }

          // Convert float32 to int16 for transmission (smaller payload)
          const int16 = new Int16Array(combined.length);
          for (let i = 0; i < combined.length; i++) {
            const s = Math.max(-1, Math.min(1, combined[i]));
            int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }

          // Convert to base64
          const bytes = new Uint8Array(int16.buffer);
          let binary = "";
          for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
          }
          const base64Audio = btoa(binary);

          console.log(`📤 Sending PCM audio: ${combined.length} samples, ${base64Audio.length} b64 chars`);

          socket.emit("audio_chunk", {
            session_id: sessionId,
            audio: base64Audio,  // Raw base64 (no data URL prefix) = raw PCM int16
          });
        }, 2000);

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
      clearInterval(intervalRef.current);

      if (processorRef.current) {
        processorRef.current.disconnect();
      }

      if (audioCtxRef.current) {
        audioCtxRef.current.close();
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