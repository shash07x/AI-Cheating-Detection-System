import React from "react";

const decisionColor = {
  PASS: "#2ecc71",
  REVIEW: "#f39c12",
  FAIL: "#e74c3c",
};

export default function FinalReport({ report }) {
  if (!report) return null;

  const verdict = report.verdict || "PASS";
  const decision = verdict.includes("FAIL")
    ? "FAIL"
    : verdict.includes("REVIEW")
    ? "REVIEW"
    : "PASS";

  const riskScore = report.final_risk_score || report.final_score || 0;
  const failReasons = report.fail_reasons || [];
  const reviewReasons = report.review_reasons || [];

  // Color event counts: red if > 0 for critical violations
  const eventColor = (count) => (count > 0 ? "#ff1744" : "#4caf50");

  return (
    <div style={styles.container}>
      <h2 style={{ color: '#fff', marginTop: 0 }}>📄 Final Interview Report</h2>

      <div style={styles.card}>
        <p style={styles.item}><b>Session ID:</b> {report.session_id}</p>
        <p style={styles.item}>
          <b>Final Risk Score:</b>{" "}
          <span style={{
            color: riskScore > 50 ? '#ff1744' : riskScore > 30 ? '#ffa726' : '#00ff88',
            fontWeight: 'bold',
            fontSize: 18
          }}>
            {riskScore}/100
          </span>
        </p>
        <p style={styles.item}><b>Video Score:</b> {report.video_score || 0}/100</p>
        <p style={styles.item}><b>Audio Score:</b> {report.audio_score || 0}/100</p>
        <p style={styles.item}>
          <b>Tab Switches:</b>{" "}
          <span style={{ color: (report.tab_switches || 0) > 3 ? '#ff1744' : '#e0e0e0', fontWeight: 'bold' }}>
            {report.tab_switches || 0}
          </span>
          {(report.tab_switches || 0) > 3 && <span style={{ color: '#ff1744', fontSize: 12, marginLeft: 8 }}>⚠ EXCESSIVE</span>}
        </p>

        {/* Event Breakdown */}
        <h4 style={{ color: '#fff', marginBottom: 8 }}>📊 Violation Events</h4>
        <div style={styles.eventGrid}>
          <div style={{...styles.eventItem, borderColor: eventColor(report.phone_events || 0)}}>
            <span style={styles.eventLabel}>📱 Phone</span>
            <span style={{...styles.eventValue, color: eventColor(report.phone_events || 0)}}>
              {report.phone_events || 0}
            </span>
          </div>
          <div style={{...styles.eventItem, borderColor: eventColor(report.multiple_person_events || 0)}}>
            <span style={styles.eventLabel}>👥 Multi-Person</span>
            <span style={{...styles.eventValue, color: eventColor(report.multiple_person_events || 0)}}>
              {report.multiple_person_events || 0}
            </span>
          </div>
          <div style={{...styles.eventItem, borderColor: eventColor(report.camera_events || 0)}}>
            <span style={styles.eventLabel}>📷 Camera</span>
            <span style={{...styles.eventValue, color: eventColor(report.camera_events || 0)}}>
              {report.camera_events || 0}
            </span>
          </div>
          <div style={{...styles.eventItem, borderColor: eventColor(report.looking_away_events > 5 ? 1 : 0)}}>
            <span style={styles.eventLabel}>👀 Looking Away</span>
            <span style={{...styles.eventValue, color: eventColor(report.looking_away_events > 5 ? 1 : 0)}}>
              {report.looking_away_events || 0}
            </span>
          </div>
        </div>

        {/* Fail Reasons */}
        {failReasons.length > 0 && (
          <>
            <h4 style={{ color: '#ff1744', marginBottom: 8 }}>🚨 Fail Reasons</h4>
            <ul style={{...styles.reasonList, color: '#ff8a80'}}>
              {failReasons.map((r, i) => (
                <li key={i} style={styles.reasonItem}>{r}</li>
              ))}
            </ul>
          </>
        )}

        {/* Review Reasons */}
        {reviewReasons.length > 0 && failReasons.length === 0 && (
          <>
            <h4 style={{ color: '#ffa726', marginBottom: 8 }}>⚠️ Review Reasons</h4>
            <ul style={{...styles.reasonList, color: '#ffcc80'}}>
              {reviewReasons.map((r, i) => (
                <li key={i} style={styles.reasonItem}>{r}</li>
              ))}
            </ul>
          </>
        )}

        {/* Confidence */}
        <p style={styles.item}><b>Confidence:</b> {report.confidence || 0}%</p>

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

        {/* Status Message */}
        <p style={{ color: '#b0b0b0', fontSize: 12, textAlign: 'center', marginTop: 8 }}>
          {report.status_message || ""}
        </p>
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
    fontWeight: "bold",
    fontSize: 14,
  },
  reasonList: {
    margin: "8px 0 16px 0",
    paddingLeft: 20,
    fontSize: 13,
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
