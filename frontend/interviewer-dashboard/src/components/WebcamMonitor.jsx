import React, { useEffect, useRef } from "react";

/**
 * WebcamMonitor (Option A – REST-based)
 * - Captures real webcam frames
 * - Sends frames to backend via POST /video/analyze
 * - Fixes "frame required" error
 */
export default function WebcamMonitor({ active, sessionId, onVideoScore }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!active) return;

    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            frameRate: { ideal: 15 },
          },
          audio: false,
        });

        streamRef.current = stream;
        videoRef.current.srcObject = stream;
      } catch (err) {
        alert("❌ Webcam permission denied");
      }
    };

    startCamera();

    // Capture & send frames every 1.5 seconds
    intervalRef.current = setInterval(() => {
      if (!document.hidden) {
        captureAndSendFrame();
      }
    }, 1500);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, [active]);

  const captureAndSendFrame = async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas) return;
    if (video.videoWidth === 0) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert frame → base64 JPEG
    const frameBase64 = canvas.toDataURL("image/jpeg", 0.7);

    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:5000"}/video/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          session_id: sessionId,
          frame: frameBase64 
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        if (onVideoScore && data.video_score !== undefined) {
          onVideoScore(data.video_score);
        }
      }
    } catch (err) {
      console.error("Frame send failed", err);
    }
  };

  return (
    <div>
      <h4>🎥 Live Webcam Feed</h4>

      <video
        ref={videoRef}
        autoPlay
        muted
        playsInline
        style={{
          width: "100%",
          borderRadius: 8,
          border: "2px solid #ddd",
        }}
      />

      {/* Hidden canvas for frame extraction */}
      <canvas ref={canvasRef} style={{ display: "none" }} />
    </div>
  );
}
