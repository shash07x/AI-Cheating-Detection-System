import React, { useEffect, useState } from "react";
import socket from "../socket/socket";
import FinalReport from "./FinalReport";
import AlertPopup from "./AlertPopup";
import RiskTimelineGraph from "./RiskTimelineGraph";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";

const BACKEND = process.env.REACT_APP_BACKEND_URL || "https://shxsh07-ai-cheating-backend.hf.space";

const riskColors = {
  low: "#4CAF50",
  medium: "#FF9800",
  high: "#FF9800",
  critical: "#F44336",
  none: "#4CAF50",
};

export default function Dashboard() {
  const sessionId = "session_01";

  const [sessionActive, setSessionActive] = useState(false);
  const [risk, setRisk] = useState("none");
  const [alerts, setAlerts] = useState([]);
  const [finalReport, setFinalReport] = useState(null);
  const [popupAlert, setPopupAlert] = useState(null);
  const [pendingCandidate, setPendingCandidate] = useState(null);

  const [audioScore, setAudioScore] = useState(0);
  const [audioHistory, setAudioHistory] = useState([]);
  const [videoScore, setVideoScore] = useState(0);
  const [finalScore, setFinalScore] = useState(0);
  const [tabSwitches, setTabSwitches] = useState(0);

  const [timeline, setTimeline] = useState([]);
  const [sessionLink, setSessionLink] = useState(null);
  const [backendConnected, setBackendConnected] = useState(false);

  /* -------- CREATE SESSION -------- */
  const createSession = async () => {
    try {
      const res = await fetch(`${BACKEND}/session/create`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

      const data = await res.json();
      const sid = data.session_id || sessionId;
      setSessionLink(`https://ai-cheating-candidate-app.vercel.app/?session=${sid}`);
      alert("Session created! Link is ready to share.");
    } catch (error) {
      console.error("Failed to create session:", error);
      alert(`Failed to create session. Check if backend is running`);
    }
  };

  /* -------- START MONITORING -------- */
  const startMonitoring = async () => {
    try {
      const res = await fetch(`${BACKEND}/ai/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

      setSessionActive(true);
      setRisk("none");
      setAlerts([]);
      setFinalReport(null);
      setPopupAlert(null);
      setAudioScore(0);
      setAudioHistory([]);
      setVideoScore(0);
      setFinalScore(0);
      setTabSwitches(0);
      setTimeline([]);

      alert("Monitoring started successfully!");
    } catch (error) {
      console.error("Failed to start monitoring:", error);
      alert("Failed to start monitoring.");
    }
  };

  /* -------- STOP MONITORING -------- */
  const stopMonitoring = async () => {
    try {
      await fetch(`${BACKEND}/ai/finalize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, tab_switches: tabSwitches }),
      });

      const res = await fetch(`${BACKEND}/ai/timeline/${sessionId}`);
      if (res.ok) {
        const json = await res.json();
        setTimeline(json.events || []);
      }

      setSessionActive(false);
      alert("Monitoring stopped!");
    } catch (error) {
      console.error("Failed to stop monitoring:", error);
      setSessionActive(false);
    }
  };

  /* -------- TAB SWITCH DETECTION -------- */
  useEffect(() => {
    const onBlur = () => {
      if (sessionActive) {
        setTabSwitches((prev) => prev + 1);
        socket.emit("tab_switch", { session_id: sessionId });
      }
    };

    window.addEventListener("blur", onBlur);
    return () => window.removeEventListener("blur", onBlur);
  }, [sessionActive, sessionId]);

  /* -------- CANDIDATE ADMISSION HANDLER -------- */
  const handleAdmit = (candidateId, admitted) => {
    socket.emit("candidate_admission_response", {
      candidate_id: candidateId,
      session_id: sessionId,
      admitted,
      reason: admitted ? "" : "Entry declined by interviewer.",
    });
    setPendingCandidate(null);
  };

  /* -------- SOCKET LISTENERS (COMPLETE FIX) -------- */
  useEffect(() => {
    console.log("🔌 Setting up socket listeners");

    // Connection status tracking
    socket.on("connect", () => {
      console.log("✅ Connected to backend");
      setBackendConnected(true);
    });
    socket.on("disconnect", () => {
      console.log("❌ Disconnected from backend");
      setBackendConnected(false);
    });

    socket.on("connect", () => {
      console.log("✅ Socket connected:", socket.id);
    });

    // -------- CANDIDATE JOIN REQUEST --------
    socket.on("candidate_join_request", (data) => {
      console.log("📩 CANDIDATE JOIN REQUEST:", data);
      setPendingCandidate(data);
    });

    // AI Live Update - WITH PROPER STATUS HANDLING
    socket.on("ai_live_update", (data) => {
      console.log("📊 AI LIVE UPDATE:", data);

      if (data.session_id === sessionId) {
        const status = data.status || "";

        if (data.is_speaking === false && status === "waiting_for_speech") {
          setAudioScore(0);
          console.log("🔇 SILENT - Gauges reset to 0");
          setAudioHistory(prev => [...prev, {
            time: new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            ai: 0, human: 0
          }].slice(-30));
        } else if (status === "speech_detected" || status === "speech_detected_no_transcript") {
          setAudioScore(data.ai_percent);
          console.log(`🎤 SPEECH DETECTED - Energy AI Score: ${data.ai_percent}%`);
          setAudioHistory(prev => [...prev, {
            time: new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            ai: data.ai_percent, human: data.human_percent || (100 - data.ai_percent)
          }].slice(-30));
        } else if (status === "buffering") {
          console.log("🎤 BUFFERING - Speech detected, awaiting analysis...");
          setAudioHistory(prev => {
            const lastScore = prev.length > 0 ? prev[prev.length - 1].ai : 0;
            return [...prev, {
              time: new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
              ai: lastScore, human: 100 - lastScore
            }].slice(-30);
          });
        } else if (data.is_speaking === true) {
          setAudioScore(data.ai_percent);
          console.log(`🎙️ SPEAKING - AI: ${data.ai_percent}%`);
          setAudioHistory(prev => [...prev, {
            time: new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            ai: data.ai_percent, human: 100 - data.ai_percent
          }].slice(-30));
        }
      }
    });


    // Risk Update
    socket.on("risk_update", (data) => {
      console.log("📊 RISK UPDATE:", data);

      if (data.session_id === sessionId) {
        if (data.video_score !== undefined) {
          setVideoScore(data.video_score);
          console.log(`🎥 Video: ${data.video_score}`);
        }

        if (data.audio_score !== undefined) {
          setAudioScore(data.audio_score);
          console.log(`🎤 Audio: ${data.audio_score}`);
        }

        if (data.final_score !== undefined) {
          setFinalScore(data.final_score);
          console.log(`🎯 Final: ${data.final_score}`);
        }
        if (data.violation_level) {
          setRisk(data.violation_level);
          console.log(`🔥 Risk: ${data.violation_level}`);
        }
      }
    });

    // Fraud Alert
    socket.on("fraud_alert", (data) => {
      console.log("🚨 FRAUD ALERT:", data);

      if (data.session_id === sessionId) {
        const enriched = {
          ...data,
          time: data.time || new Date().toLocaleTimeString(),
        };

        setAlerts((prev) => [enriched, ...prev.slice(0, 19)]);

        if (data.violation_level) {
          setRisk(data.violation_level);
        }

        if (data.video_score !== undefined) setVideoScore(data.video_score);
        if (data.audio_score !== undefined) {
          setAudioScore(data.audio_score);
        }
        if (data.final_score !== undefined) setFinalScore(data.final_score);

        console.log(`✅ Alert added`);
      }
    });

    // Final Report
    socket.on("final_report", (report) => {
      console.log("📄 FINAL REPORT:", report);
      setFinalReport(report);
    });

    socket.on("connect_error", (error) => {
      console.error("❌ Socket error:", error);
    });

    return () => {
      socket.off("connect");
      socket.off("ai_live_update");
      socket.off("risk_update");
      socket.off("fraud_alert");
      socket.off("final_report");
      socket.off("connect_error");
      socket.off("candidate_join_request");
    };
  }, [sessionId]);

  /* ---------------- UI ---------------- */
  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div>
          <h1 style={{ margin: 0, color: '#fff' }}>🧠 AI Interview Proctoring Dashboard</h1>
          <p style={{ margin: "5px 0", color: '#e0e0e0' }}>
            Session: <b style={{ color: '#ff00ff' }}>{sessionId}</b>
          </p>
          <p style={{ margin: "5px 0", color: '#e0e0e0' }}>
            Status:{" "}
            <b style={{ color: sessionActive ? "#00ff88" : "#ff1744" }}>
              {sessionActive ? "🟢 Monitoring Active" : "🔴 Stopped"}
            </b>
            {" | Backend: "}
            <b style={{ color: backendConnected ? "#00ff88" : "#ffa726" }}>
              {backendConnected ? "🟢 Connected" : "🟡 Connecting..."}
            </b>
          </p>
        </div>
        {sessionActive && <span style={styles.live}>🟢 LIVE</span>}
      </header>

      <div style={styles.grid}>
        {/* CONTROLS */}
        <div style={styles.card}>
          <h3 style={{ marginTop: 0, color: '#fff' }}>🎛 Session Controls</h3>
          <button onClick={createSession} style={styles.createBtn}>
            ➕ Create Interview Session
          </button>

          {sessionLink && (
            <div style={styles.linkBox}>
              <p style={{ margin: "5px 0", color: '#e0e0e0' }}>
                <b>📋 Candidate Link:</b>
              </p>
              <input
                value={sessionLink}
                readOnly
                style={styles.linkInput}
                onClick={(e) => e.target.select()}
              />
              <button
                onClick={() => {
                  navigator.clipboard.writeText(sessionLink);
                  alert("Link copied!");
                }}
                style={styles.copyBtn}
              >
                📋 Copy
              </button>
            </div>
          )}

          <div style={{ marginTop: 15 }}>
            <button
              style={{ ...styles.start, opacity: sessionActive ? 0.5 : 1 }}
              disabled={sessionActive}
              onClick={startMonitoring}
            >
              ▶ Start Monitoring
            </button>
            <button
              style={{ ...styles.stop, opacity: !sessionActive ? 0.5 : 1 }}
              disabled={!sessionActive}
              onClick={stopMonitoring}
            >
              ⏹ End Session
            </button>
          </div>
        </div>

        {/* CURRENT RISK */}
        <div style={styles.card}>
          <h3 style={{ marginTop: 0, color: '#fff' }}>🔥 Current Risk Level</h3>
          {risk === "none" || risk === "low" ? (
            <p style={styles.noRisk}>✅ No active violations detected</p>
          ) : (
            <>
              <h2 style={{ color: riskColors[risk], margin: "10px 0" }}>
                {risk.toUpperCase()}
              </h2>
              <div style={styles.meterBg}>
                <div
                  style={{
                    ...styles.meterFill,
                    background: riskColors[risk],
                    width: risk === "critical" ? "100%" : risk === "high" ? "75%" : "50%",
                  }}
                />
              </div>
              <p style={{ marginTop: 8, fontSize: 14, color: "#e0e0e0" }}>
                {risk === "medium" && "Moderate concern - investigating"}
                {risk === "high" && "⚠️ High risk - close attention required"}
                {risk === "critical" && "🚨 CRITICAL - intervention required"}
              </p>
            </>
          )}
        </div>

        {/* SCORE BREAKDOWN */}
        <div style={styles.card}>
          <h3 style={{ marginTop: 0, color: '#fff' }}>📊 Score Breakdown</h3>
          <div style={styles.scoreItem}>
            <span style={{ color: '#e0e0e0' }}>🎥 Video Score:</span>
            <b style={{ color: videoScore > 70 ? "#ff1744" : "#00ff88" }}>
              {videoScore}/100
            </b>
          </div>
          <div style={styles.scoreItem}>
            <span style={{ color: '#e0e0e0' }}>🎤 Audio Score:</span>
            <b style={{ color: audioScore > 70 ? "#ff1744" : "#00ff88" }}>
              {audioScore}/100
            </b>
          </div>
          <div style={styles.scoreItem}>
            <span style={{ color: '#e0e0e0' }}>🎯 Final Score:</span>
            <b style={{ color: finalScore > 70 ? "#ff1744" : "#00ff88" }}>
              {finalScore}/100
            </b>
          </div>
          <div style={styles.scoreItem}>
            <span style={{ color: '#e0e0e0' }}>🪟 Tab Switches:</span>
            <b style={{ color: tabSwitches > 3 ? "#ff1744" : "#00ff88" }}>
              {tabSwitches}
            </b>
          </div>
        </div>

        {/* AI GAUGE WITH SPEAKING INDICATOR */}
        <div style={styles.card}>
          <h3 style={{ marginTop: 0, color: '#fff' }}>🤖 AI Voice Detection</h3>

          {/* Speaking Status Indicator */}
          <div style={{
            textAlign: 'center',
            padding: '10px',
            marginBottom: '15px',
            borderRadius: '8px',
            background: audioScore > 0 ? 'rgba(0, 255, 136, 0.1)' : 'rgba(136, 136, 136, 0.1)',
            border: `2px solid ${audioScore > 0 ? '#00ff88' : '#444'}`
          }}>
            {audioScore > 0 ? (
              <p style={{
                color: '#00ff88',
                fontSize: 16,
                fontWeight: 'bold',
                margin: 0
              }}>
                🎙️ DETECTING SPEECH...
              </p>
            ) : (
              <p style={{
                color: '#888',
                fontSize: 16,
                margin: 0
              }}>
                🔇 Waiting for speech...
              </p>
            )}
          </div>

          <div style={{ width: '100%', height: 260, marginTop: 10 }}>
            {audioHistory.length === 0 ? (
              <p style={{ textAlign: 'center', color: '#888', marginTop: 100 }}>Waiting for audio data...</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={audioHistory}>
                  <XAxis dataKey="time" stroke="#e0e0e0" fontSize={12} tick={{ fill: "#e0e0e0" }} />
                  <YAxis domain={[0, 100]} stroke="#e0e0e0" fontSize={12} tick={{ fill: "#e0e0e0" }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'rgba(20, 20, 30, 0.9)', borderColor: 'rgba(255, 0, 255, 0.3)', color: '#fff' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Legend wrapperStyle={{ paddingTop: 20 }} />
                  <Line type="monotone" dataKey="ai" name="🤖 AI Detection" stroke="#ff00ff" strokeWidth={3} dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="human" name="👤 Human Speech" stroke="#00ff88" strokeWidth={3} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* LIVE ALERTS */}
        <div style={{ ...styles.card, gridColumn: "1 / span 2" }}>
          <h3 style={{ marginTop: 0, color: '#fff' }}>🔔 Live Fraud Alerts</h3>
          {alerts.length === 0 && (
            <p style={styles.noAlerts}>No alerts yet - monitoring...</p>
          )}
          <div style={styles.alertContainer}>
            {alerts.slice(0, 10).map((a, i) => (
              <div
                key={i}
                style={{
                  ...styles.alert,
                  borderLeft: `6px solid ${riskColors[a.violation_level] || "#ff00ff"}`,
                }}
              >
                <div style={styles.alertHeader}>
                  <span style={{ ...styles.alertBadge, background: riskColors[a.violation_level] }}>
                    {a.violation_level?.toUpperCase()}
                  </span>
                  <small style={styles.alertTime}>⏱ {a.time}</small>
                </div>
                <p style={styles.alertScore}>
                  <b>Risk Score:</b> {a.final_score || 0}/100
                </p>
                <ul style={styles.alertReasons}>
                  {a.reasons?.map((r, idx) => (
                    <li key={idx}>{r}</li>
                  ))}
                </ul>
                {a.evidence && (
                  <div style={styles.evidenceContainer}>
                    <img
                      src={`${BACKEND}/${a.evidence}`}
                      alt="Evidence"
                      style={styles.evidenceImage}
                      onError={(e) => e.target.style.display = 'none'}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* TIMELINE */}
        {!sessionActive && timeline.length > 0 && (
          <div style={{ ...styles.card, gridColumn: "1 / span 2" }}>
            <h3 style={{ marginTop: 0, color: '#fff' }}>📈 Risk Timeline</h3>
            <RiskTimelineGraph data={timeline} />
          </div>
        )}

        {/* FINAL REPORT */}
        {!sessionActive && finalReport && (
          <div style={{ ...styles.card, gridColumn: "1 / span 2" }}>
            <h3 style={{ marginTop: 0, color: '#fff' }}>📄 Final Report</h3>
            <FinalReport report={finalReport} />
          </div>
        )}
      </div>

      <AlertPopup alert={popupAlert} onClose={() => setPopupAlert(null)} />

      {/* -------- CANDIDATE ADMISSION POPUP -------- */}
      {pendingCandidate && (
        <div style={styles.admissionOverlay}>
          <div style={styles.admissionModal}>
            <div style={styles.admissionIcon}>👤</div>
            <h2 style={{ color: '#fff', margin: '0 0 8px 0', fontSize: 20 }}>Candidate Join Request</h2>
            <p style={{ color: '#b0b0b0', margin: '0 0 24px 0', fontSize: 14 }}>
              A candidate wants to join the interview session.
            </p>
            <div style={styles.admissionIdBox}>
              <span style={{ color: '#b0b0b0', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Candidate ID</span>
              <span style={{ color: '#ff00ff', fontSize: 18, fontWeight: 'bold', fontFamily: 'monospace' }}>
                {pendingCandidate.candidate_id}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 12, marginTop: 24, width: '100%' }}>
              <button
                onClick={() => handleAdmit(pendingCandidate.candidate_id, false)}
                style={styles.admissionDecline}
              >
                ✕ Decline
              </button>
              <button
                onClick={() => handleAdmit(pendingCandidate.candidate_id, true)}
                style={styles.admissionAccept}
              >
                ✓ Accept
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* STYLES */
const styles = {
  page: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    background: "linear-gradient(135deg, #0a0a0a 0%, #2d1b69 50%, #ff006e 100%)",
    minHeight: "100vh",
    padding: 20,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
    background: "rgba(20, 20, 30, 0.95)",
    padding: 20,
    borderRadius: 12,
    boxShadow: "0 8px 32px rgba(255, 0, 255, 0.3)",
    border: "1px solid rgba(255, 0, 255, 0.2)",
  },
  live: {
    background: "linear-gradient(90deg, #00ff88, #00d4ff)",
    color: "#000",
    padding: "8px 16px",
    borderRadius: 20,
    fontWeight: "bold",
    fontSize: 14,
    boxShadow: "0 0 20px rgba(0, 255, 136, 0.5)",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, 1fr)",
    gap: 20,
  },
  card: {
    background: "rgba(20, 20, 30, 0.9)",
    borderRadius: 12,
    padding: 20,
    boxShadow: "0 8px 32px rgba(138, 43, 226, 0.2)",
    border: "1px solid rgba(138, 43, 226, 0.3)",
    backdropFilter: "blur(10px)",
  },
  createBtn: {
    background: "linear-gradient(135deg, #8e2de2, #4a00e0)",
    color: "#fff",
    border: "none",
    padding: "12px 16px",
    borderRadius: 8,
    cursor: "pointer",
    width: "100%",
    fontWeight: "bold",
    marginBottom: 10,
    fontSize: 14,
    boxShadow: "0 4px 15px rgba(138, 43, 226, 0.4)",
  },
  linkBox: {
    background: "rgba(138, 43, 226, 0.1)",
    padding: 12,
    borderRadius: 6,
    marginTop: 10,
    border: "1px solid rgba(138, 43, 226, 0.3)",
  },
  linkInput: {
    width: "100%",
    padding: 8,
    border: "1px solid rgba(138, 43, 226, 0.5)",
    borderRadius: 4,
    marginTop: 5,
    fontSize: 12,
    fontFamily: "monospace",
    background: "rgba(0, 0, 0, 0.5)",
    color: "#fff",
  },
  copyBtn: {
    background: "linear-gradient(135deg, #ff00ff, #ff1744)",
    color: "#fff",
    border: "none",
    padding: "6px 12px",
    borderRadius: 4,
    cursor: "pointer",
    marginTop: 8,
    fontSize: 12,
  },
  start: {
    background: "linear-gradient(135deg, #00ff88, #00d4ff)",
    color: "#000",
    border: "none",
    padding: "12px 16px",
    borderRadius: 8,
    marginRight: 10,
    fontWeight: "bold",
    fontSize: 14,
  },
  stop: {
    background: "linear-gradient(135deg, #ff1744, #f50057)",
    color: "#fff",
    border: "none",
    padding: "12px 16px",
    borderRadius: 8,
    fontWeight: "bold",
    fontSize: 14,
  },
  noRisk: {
    color: "#00ff88",
    fontSize: 16,
    fontWeight: "500",
  },
  meterBg: {
    width: "100%",
    height: 20,
    background: "rgba(0, 0, 0, 0.5)",
    borderRadius: 10,
    overflow: "hidden",
    marginTop: 10,
    border: "1px solid rgba(138, 43, 226, 0.3)",
  },
  meterFill: {
    height: "100%",
    transition: "width 0.5s ease",
    borderRadius: 10,
  },
  scoreItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 0",
    borderBottom: "1px solid rgba(138, 43, 226, 0.2)",
  },
  noAlerts: {
    color: "#b0b0b0",
    fontStyle: "italic",
  },
  alertContainer: {
    maxHeight: "400px",
    overflowY: "auto",
  },
  alert: {
    background: "rgba(30, 30, 40, 0.8)",
    padding: 14,
    borderRadius: 8,
    marginBottom: 12,
    border: "1px solid rgba(138, 43, 226, 0.2)",
  },
  alertHeader: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  alertBadge: {
    color: "#fff",
    padding: "5px 12px",
    borderRadius: 12,
    fontSize: 11,
    fontWeight: "bold",
  },
  alertTime: {
    color: "#b0b0b0",
    fontSize: 12,
  },
  alertScore: {
    margin: "8px 0",
    fontSize: 14,
    color: '#e0e0e0',
  },
  alertReasons: {
    margin: "8px 0",
    paddingLeft: 20,
    fontSize: 13,
    color: "#b0b0b0",
  },
  evidenceContainer: {
    marginTop: 10,
    padding: 10,
    background: "rgba(0, 0, 0, 0.5)",
    borderRadius: 6,
    border: "2px solid #ff1744",
  },
  evidenceImage: {
    width: "100%",
    maxWidth: 300,
    borderRadius: 4,
  },
  admissionOverlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(0, 0, 0, 0.7)",
    backdropFilter: "blur(6px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 9999,
  },
  admissionModal: {
    background: "rgba(20, 20, 35, 0.98)",
    borderRadius: 16,
    padding: "36px 32px",
    width: 400,
    maxWidth: "90vw",
    border: "1px solid rgba(255, 0, 255, 0.3)",
    boxShadow: "0 0 60px rgba(255, 0, 255, 0.15), 0 8px 32px rgba(0,0,0,0.5)",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    textAlign: "center",
  },
  admissionIcon: {
    width: 64,
    height: 64,
    borderRadius: 16,
    background: "rgba(138, 43, 226, 0.15)",
    border: "1px solid rgba(138, 43, 226, 0.3)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 28,
    marginBottom: 16,
  },
  admissionIdBox: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    padding: "16px 24px",
    borderRadius: 10,
    background: "rgba(0, 0, 0, 0.4)",
    border: "1px solid rgba(138, 43, 226, 0.2)",
    width: "100%",
  },
  admissionAccept: {
    flex: 1,
    padding: "12px 0",
    borderRadius: 10,
    border: "none",
    background: "linear-gradient(135deg, #00ff88, #00d4ff)",
    color: "#000",
    fontWeight: "bold",
    fontSize: 14,
    cursor: "pointer",
    boxShadow: "0 4px 15px rgba(0, 255, 136, 0.3)",
  },
  admissionDecline: {
    flex: 1,
    padding: "12px 0",
    borderRadius: 10,
    border: "1px solid rgba(244, 67, 54, 0.4)",
    background: "rgba(244, 67, 54, 0.1)",
    color: "#f44336",
    fontWeight: "bold",
    fontSize: 14,
    cursor: "pointer",
  },
};