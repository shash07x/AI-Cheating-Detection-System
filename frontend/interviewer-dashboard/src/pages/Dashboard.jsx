import React, { useEffect, useState } from "react";
import socket from "../socket/socket";
import api from "../api/backend";
import RiskMeter from "../components/RiskMeter";
import FraudAlerts from "../components/FraudAlerts";
import WebcamMonitor from "../components/WebcamMonitor";

/* ---------------- CONSTANTS ---------------- */

const sessionId = "session_01";

/* ---------------- COMPONENT ---------------- */

export default function Dashboard() {
  const [alerts, setAlerts] = useState([]);
  const [sessionActive, setSessionActive] = useState(false);

  // AUDIO
  const [audioScore, setAudioScore] = useState(0);

  // VIDEO
  const [videoScore, setVideoScore] = useState(0);

  // TAB SWITCH
  const [tabViolations, setTabViolations] = useState(0);

  /* -------- SOCKET LISTENER (READ ONLY) -------- */

  useEffect(() => {
    socket.on("fraud_alert", (data) => {
      setAlerts((prev) => [
        { ...data, time: new Date().toLocaleTimeString() },
        ...prev,
      ]);
    });

    return () => socket.off("fraud_alert");
  }, []);

  /* ---------------- MICROPHONE MONITOR ---------------- */

  useEffect(() => {
    if (!sessionActive) return;

    let audioStream;
    let audioContext;
    let analyser;
    let interval;

    const startMic = async () => {
      try {
        audioStream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

        audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(audioStream);
        analyser = audioContext.createAnalyser();
        source.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);

        interval = setInterval(() => {
          analyser.getByteFrequencyData(dataArray);
          const avg =
            dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

          const score = Math.min(100, Math.max(10, Math.floor(avg)));
          setAudioScore(score);
        }, 3000);
      } catch {
        alert("Microphone permission denied");
      }
    };

    startMic();

    return () => {
      clearInterval(interval);
      audioStream?.getTracks().forEach((t) => t.stop());
      audioContext?.close();
    };
  }, [sessionActive]);

  /* ---------------- TAB SWITCH DETECTION ---------------- */

  useEffect(() => {
    if (!sessionActive) return;

    const handleVisibility = () => {
      if (document.hidden) {
        setTabViolations((prev) => prev + 1);
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);

    return () =>
      document.removeEventListener(
        "visibilitychange",
        handleVisibility
      );
  }, [sessionActive]);

  /* ---------------- SESSION CONTROLS ---------------- */

  const startMonitoring = async () => {
    await api.post("/ai/start", { session_id: sessionId });
    setSessionActive(true);
  };

  const stopMonitoring = async () => {
    await api.post("/ai/finalize", {
      session_id: sessionId,
      video_score: videoScore,
      audio_score: audioScore,
      tab_switches: tabViolations,
    });

    setSessionActive(false);
  };

  /* ---------------- UI ---------------- */

  return (
    <div style={{ padding: 20 }}>
      <h1>Interview Monitoring Dashboard</h1>

      <p><b>Session:</b> {sessionId}</p>

      <p>
        <b>Status:</b>{" "}
        <span style={{ color: sessionActive ? "green" : "red" }}>
          {sessionActive ? "Monitoring Active" : "Stopped"}
        </span>
      </p>

      <button
        onClick={startMonitoring}
        disabled={sessionActive}
        style={{ marginRight: 10 }}
      >
        ▶ Start Monitoring
      </button>

      <button
        onClick={stopMonitoring}
        disabled={!sessionActive}
      >
        ⏹ End Session
      </button>

      {/* WEBCAM */}
      {sessionActive && (
        <WebcamMonitor
          active={sessionActive}
          onVideoScore={(score) => setVideoScore(score)}
        />
      )}

      {/* AUDIO */}
      {sessionActive && (
        <p>🎤 <b>Live Audio Score:</b> {audioScore}</p>
      )}

      {/* TAB */}
      <p>🧭 <b>Tab Switch Count:</b> {tabViolations}</p>

      <RiskMeter alerts={alerts} />
      <FraudAlerts alerts={alerts} />
    </div>
  );
}
