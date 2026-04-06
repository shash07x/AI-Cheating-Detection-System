import React, { useEffect } from "react";
import WebcamCapture from "../components/WebcamCapture";
import MicCapture from "../components/MicCapture";
import TabMonitor from "../components/TabMonitor";

export default function CandidateInterview() {
  return (
    <div>
      <h2>Live Interview</h2>

      {/* REAL webcam stream */}
      <WebcamCapture />

      {/* REAL mic stream */}
      <MicCapture />

      {/* REAL tab tracking */}
      <TabMonitor />
    </div>
  );
}
