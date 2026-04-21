import { useState } from "react";
import WebcamSender from "./WebcamSender";
import MicrophoneSender from "./MicrophoneSender";
import TabTracker from "./TabTracker";
import SpeakingScene from "./SpeakingScene";
import "./App.css";

export default function CandidateApp() {
  const [audioLevel, setAudioLevel] = useState(0);
  const [micStatus, setMicStatus] = useState({ state: "requesting" });
  const [cameraStatus, setCameraStatus] = useState({ state: "requesting" });
  const sessionId = "session_01";

  const isSpeaking = audioLevel > 0.05;
  const levelPercent = Math.round(Math.min(audioLevel * 100, 100));

  const getMicLabel = () => {
    switch (micStatus.state) {
      case "active": return "Active";
      case "denied": return "Denied";
      case "error": return "Error";
      default: return "Requesting...";
    }
  };

  const getCamLabel = () => {
    switch (cameraStatus.state) {
      case "active": return "Active";
      case "denied": return "Denied";
      case "error": return "Error";
      default: return "Requesting...";
    }
  };

  const getVoiceLabel = () => {
    return isSpeaking ? "Speaking detected" : "Silent";
  };

  return (
    <div className="candidate-page">
      {/* Three.js background scene — receives live mic energy */}
      <SpeakingScene audioLevel={audioLevel} />

      {/* Gradient overlay above the scene */}
      <div className="scene-overlay" />

      {/* ── Audio Level Widget (top-right) ──────────────────── */}
      <div className="audio-widget">
        <div className="audio-widget-bar-track">
          <div
            className="audio-widget-bar-fill"
            style={{ width: `${levelPercent}%` }}
          />
        </div>
        <div className="audio-widget-percent">{levelPercent}%</div>
        <p className="audio-widget-desc">
          The 3D background intensifies with your voice energy to make the page
          feel alive instead of static.
        </p>
      </div>

      {/* ── Bottom-left content ─────────────────────────────── */}
      <div className="content-bottom">
        <span className="session-badge">CANDIDATE INTERVIEW SESSION</span>

        <h1 className="page-title">
          Candidate<br />Proctoring System
        </h1>

        <p className="page-subtitle">
          Keep your microphone and camera enabled. Note: The tab switching is
          being monitored.
        </p>

        {/* Status cards row */}
        <div className="status-cards">
          <div className={`status-card mic ${micStatus.state}`}>
            <span className="status-card-label">MICROPHONE</span>
            <span className="status-card-value">{getMicLabel()}</span>
          </div>

          <div className={`status-card cam ${cameraStatus.state}`}>
            <span className="status-card-label">CAMERA</span>
            <span className="status-card-value">{getCamLabel()}</span>
          </div>

          <div className={`status-card voice ${isSpeaking ? "speaking" : "silent"}`}>
            <span className="status-card-label">VOICE ACTIVITY</span>
            <span className="status-card-value">{getVoiceLabel()}</span>
          </div>
        </div>
      </div>

      {/* Hidden functional components — these keep the pipelines alive */}
      <WebcamSender sessionId={sessionId} onStatusChange={setCameraStatus} />
      <MicrophoneSender
        sessionId={sessionId}
        onAudioLevel={setAudioLevel}
        onStatusChange={setMicStatus}
      />
      <TabTracker sessionId={sessionId} />
    </div>
  );
}
