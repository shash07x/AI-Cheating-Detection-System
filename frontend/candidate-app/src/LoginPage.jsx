import { useState, useEffect } from "react";
import socket from "./socket/candidateSocket";
import "./LoginPage.css";

export default function LoginPage({ onAdmitted }) {
  const [candidateId, setCandidateId] = useState("");
  const [status, setStatus] = useState("idle"); // idle | waiting | rejected
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    // Listen for admission response from backend
    const handleResponse = (data) => {
      console.log("📩 Admission response:", data);
      if (data.admitted) {
        setStatus("admitted");
        // Pass candidateId to parent so it can be used in proctoring
        onAdmitted(data.candidate_id || candidateId, data.session_id || "session_01");
      } else {
        setStatus("rejected");
        setErrorMsg(data.reason || "Your entry was declined by the interviewer.");
      }
    };

    socket.on("admission_response", handleResponse);

    return () => {
      socket.off("admission_response", handleResponse);
    };
  }, [candidateId, onAdmitted]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = candidateId.trim();
    if (!trimmed) return;

    setStatus("waiting");
    setErrorMsg("");

    // Emit join request to backend, which forwards to interviewer
    socket.emit("candidate_join_request", {
      candidate_id: trimmed,
      session_id: "session_01",
    });

    console.log("📤 Join request sent for candidate:", trimmed);
  };

  const handleRetry = () => {
    setStatus("idle");
    setErrorMsg("");
    setCandidateId("");
  };

  return (
    <div className="login-page">
      {/* Animated background particles */}
      <div className="login-particles">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="particle"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 8}s`,
              animationDuration: `${6 + Math.random() * 8}s`,
            }}
          />
        ))}
      </div>

      <div className="login-container">
        {/* Glass card */}
        <div className="login-card">
          {/* Logo / Icon */}
          <div className="login-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>

          <h1 className="login-title">Candidate Portal</h1>
          <p className="login-subtitle">
            Enter your Candidate ID to request access to the interview session.
          </p>

          {/* IDLE: Show form */}
          {status === "idle" && (
            <form onSubmit={handleSubmit} className="login-form">
              <div className="input-group">
                <label htmlFor="candidateId" className="input-label">CANDIDATE ID</label>
                <input
                  id="candidateId"
                  type="text"
                  value={candidateId}
                  onChange={(e) => setCandidateId(e.target.value)}
                  placeholder="e.g. CAND-2026-001"
                  className="login-input"
                  autoFocus
                  required
                />
              </div>
              <button type="submit" className="login-btn" disabled={!candidateId.trim()}>
                <span>Request Access</span>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </button>
            </form>
          )}

          {/* WAITING: Show spinner */}
          {status === "waiting" && (
            <div className="login-status waiting">
              <div className="spinner" />
              <p className="status-text">Waiting for interviewer approval...</p>
              <p className="status-sub">Candidate ID: <strong>{candidateId}</strong></p>
            </div>
          )}

          {/* REJECTED: Show message */}
          {status === "rejected" && (
            <div className="login-status rejected">
              <div className="rejected-icon">✕</div>
              <p className="status-text rejected-text">{errorMsg}</p>
              <button onClick={handleRetry} className="retry-btn">
                Try Again
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <p className="login-footer">
          AI Interview Proctoring System • Secure Session
        </p>
      </div>
    </div>
  );
}
