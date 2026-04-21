import { useEffect, useRef } from "react";

export default function WebcamSender({ sessionId, onStatusChange }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  // START CAMERA
  useEffect(() => {
    async function startCamera() {
      try {
        if (onStatusChange) onStatusChange({ state: "requesting" });

        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: 640,
            height: 480,
          },
          audio: false,
        });

        const video = videoRef.current;
        video.srcObject = stream;

        video.onloadedmetadata = () => {
          video.play();
          console.log("Camera ready");
          if (onStatusChange) onStatusChange({ state: "active" });
        };

      } catch (err) {
        console.error("Camera error:", err);
        if (onStatusChange) {
          if (err.name === "NotAllowedError") {
            onStatusChange({ state: "denied" });
          } else {
            onStatusChange({ state: "error" });
          }
        }
      }
    }

    startCamera();
  }, [onStatusChange]);

  // SEND FRAMES TO BACKEND
  useEffect(() => {
  const interval = setInterval(() => {

    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas) return;

    // Wait until camera frame is actually available
    if (
      video.readyState !== 4 ||
      video.videoWidth === 0 ||
      video.videoHeight === 0
    ) {
      console.log("⏳ Camera waiting for frame...");
      return;
    }

    const ctx = canvas.getContext("2d");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const frame = canvas.toDataURL("image/jpeg", 0.8);

    fetch(`${process.env.REACT_APP_BACKEND_URL || "https://shxsh07-ai-cheating-backend.hf.space"}/video/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: sessionId,
        frame: frame,
      }),
    }).catch((err) => console.error("Video send error:", err));

  }, 8000); // 8s interval — HF free tier CPU processes ~1 frame/35s

  return () => clearInterval(interval);
}, [sessionId]);

  return (
    <>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{
          position: "absolute",
          width: "1px",
          height: "1px",
          opacity: 0,
        }}
      />

      <canvas
        ref={canvasRef}
        style={{ display: "none" }}
      />
    </>
  );
}