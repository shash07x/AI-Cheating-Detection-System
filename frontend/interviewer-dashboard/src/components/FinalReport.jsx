import React from "react";

const decisionColor = {
  PASS: "#2ecc71",
  REVIEW: "#f39c12",
  FAIL: "#e74c3c",
};

export default function FinalReport({ report }) {
  if (!report) return null;

  // Use the verdict from the backend (real-time computed) instead of re-computing here
  const verdict = report.verdict || "PASS";
  const decision = verdict.includes("FAIL")
    ? "FAIL"
    : verdict.includes("REVIEW")
    ? "REVIEW"
    : "PASS";

  const riskScore = report.final_risk_score || report.final_score || 0;

  return (
    <div style={styles.container}>
      <h2 style={{ color: '#fff', marginTop: 0 }}>📄 Final Interview Report</h2>

      <div style={styles.card}>
        <p style={styles.item}><b>Session ID:</b> {report.session_id}</p>
        <p style={styles.item}><b>Final Risk Score:</b> <span style={{ color: riskScore > 60 ? '#ff1744' : riskScore > 30 ? '#ffa726' : '#00ff88', fontWeight: 'bold' }}>{riskScore}/100</span></p>
        <p style={styles.item}><b>Video Score:</b> {report.video_score || 0}/100</p>
        <p style={styles.item}><b>Audio Score:</b> {report.audio_score || 0}/100</p>
        <p style={styles.item}><b>Tab Switches:</b> {report.tab_switches || 0}</p>

        {/* Event Breakdown */}
        <h4 style={{ color: '#fff', marginBottom: 8 }}>📊 Violation Events</h4>
        <div style={styles.eventGrid}>
          <div style={styles.eventItem}>
            <span style={styles.eventLabel}>📱 Phone</span>
            <span style={styles.eventValue}>{report.phone_events || 0}</span>
          </div>
          <div style={styles.eventItem}>
            <span style={styles.eventLabel}>👥 Multi-Person</span>
            <span style={styles.eventValue}>{report.multiple_person_events || 0}</span>
          </div>
          <div style={styles.eventItem}>
            <span style={styles.eventLabel}>📷 Camera</span>
            <span style={styles.eventValue}>{report.camera_events || 0}</span>
          </div>
          <div style={styles.eventItem}>
            <span style={styles.eventLabel}>👀 Looking Away</span>
            <span style={styles.eventValue}>{report.looking_away_events || 0}</span>
          </div>
        </div>

        {/* Confidence */}
        <p style={styles.item}><b>Confidence:</b> {report.confidence || 0}%</p>

        {/* Reasoning */}
        <h4 style={{ color: '#fff', marginBottom: 8 }}>🧠 Reasoning</h4>
        <ul style={styles.reasonList}>
          {(report.reasons || []).map((r, i) => (
            <li key={i} style={styles.reasonItem}>{r}</li>
          ))}
        </ul>

        {/* Evidence */}
        {report.evidence_files && report.evidence_files.length > 0 && (
          <>
            <h4 style={{ color: '#fff', marginBottom: 8 }}>🖼️ Evidence ({report.evidence_files.length} files)</h4>
            <p style={{ color: '#b0b0b0', fontSize: 13 }}>Screenshots captured during violations</p>
          </>
        )}

        {/* Final Decision */}
        <div
          style={{
            ...styles.decision,
            background: decisionColor[decision],
          }}
        >
          FINAL DECISION: {verdict}
        </div>
      </div>
    </div>
  );
}

/* ---------------- STYLES ---------------- */

const styles = {
  container: {
    marginTop: 20,
  },
  card: {
    background: "rgba(30, 30, 45, 0.9)",
    padding: 24,
    borderRadius: 12,
    border: "1px solid rgba(138, 43, 226, 0.2)",
  },
  item: {
    margin: "10px 0",
    fontSize: 14,
    color: "#e0e0e0",
  },
  eventGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 10,
    marginBottom: 16,
  },
  eventItem: {
    display: "flex",
    justifyContent: "space-between",
    padding: "10px 14px",
    borderRadius: 8,
    background: "rgba(0, 0, 0, 0.3)",
    border: "1px solid rgba(138, 43, 226, 0.15)",
  },
  eventLabel: {
    color: "#b0b0b0",
    fontSize: 13,
  },
  eventValue: {
    color: "#fff",
    fontWeight: "bold",
    fontSize: 14,
  },
  reasonList: {
    margin: "8px 0 16px 0",
    paddingLeft: 20,
    fontSize: 13,
    color: "#b0b0b0",
  },
  reasonItem: {
    marginBottom: 4,
  },
  decision: {
    marginTop: 20,
    padding: 15,
    color: "#fff",
    fontWeight: "bold",
    borderRadius: 8,
    textAlign: "center",
    fontSize: 18,
  },
};
