import WebcamSender from "./WebcamSender";
import MicrophoneSender from "./MicrophoneSender";
import TabTracker from "./TabTracker";

export default function CandidateApp() {
  const sessionId = "session_01";

  return (
    <div style={{ padding: 30 }}>
      <h2>🎤 Candidate Interview Session</h2>
      <p>Please keep camera and microphone ON.</p>

      {/* Webcam video streaming */}
      <WebcamSender sessionId={sessionId} />

      {/* Microphone audio streaming */}
      <MicrophoneSender sessionId={sessionId} />

      {/* Tab switching detection */}
      <TabTracker sessionId={sessionId} />
    </div>
  );
}
