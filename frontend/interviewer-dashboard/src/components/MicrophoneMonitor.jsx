import { useEffect, useRef } from "react";
import socket from "../socket/socket";

const SAMPLE_RATE = 16000;
const CHUNK_MS = 1000; // 1 second chunks

export default function MicrophoneMonitor({ active, sessionId }) {
  const audioContextRef = useRef(null);
  const processorRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    if (!active) return;

    let audioContext;
    let processor;
    let stream;

    const startMic = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });

        const source = audioContext.createMediaStreamSource(stream);

        processor = audioContext.createScriptProcessor(4096, 1, 1);

        source.connect(processor);
        processor.connect(audioContext.destination);

        processor.onaudioprocess = (e) => {
          const input = e.inputBuffer.getChannelData(0);
          const pcm = new Float32Array(input);

          // Convert Float32 → base64
          const buffer = new ArrayBuffer(pcm.length * 4);
          const view = new DataView(buffer);
          pcm.forEach((v, i) => view.setFloat32(i * 4, v, true));

          const b64 = btoa(
            String.fromCharCode(...new Uint8Array(buffer))
          );

          socket.emit("audio_chunk", {
            session_id: sessionId,
            audio: b64,
            sample_rate: SAMPLE_RATE,
          });
        };

        audioContextRef.current = audioContext;
        processorRef.current = processor;
        streamRef.current = stream;
      } catch (err) {
        alert("Microphone permission denied");
        console.error(err);
      }
    };

    startMic();

    return () => {
      processorRef.current?.disconnect();
      audioContextRef.current?.close();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [active, sessionId]);

  return null;
}
