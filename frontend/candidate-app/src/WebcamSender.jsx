import { useEffect, useRef } from "react";

export default function WebcamSender({ sessionId }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  // START CAMERA
  useEffect(() => {
    async function startCamera() {
      try {
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
        };

      } catch (err) {
        console.error("Camera error:", err);
      }
    }

    startCamera();
  }, []);

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

    fetch(`${process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:5000"}/video/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: sessionId,
        frame: frame,
      }),
    }).catch((err) => console.error("Video send error:", err));

  }, 1000);

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