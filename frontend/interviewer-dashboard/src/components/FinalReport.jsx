import React from "react";

const decisionColor = {
  PASS: "#2ecc71",
  REVIEW: "#f39c12",
  FAIL: "#e74c3c",
};

export default function FinalReport({ report }) {
  if (!report) return null;

  const decision =
    report.violation_level === "low"
      ? "PASS"
      : report.violation_level === "medium"
      ? "REVIEW"
      : "FAIL";

  return (
    <div style={styles.container}>
      <h2>📄 Final Interview Report</h2>

      <div style={styles.card}>
        <p><b>Session ID:</b> {report.session_id}</p>
        <p><b>Final Score:</b> {report.final_score}</p>
        <p><b>Violation Level:</b> {report.violation_level.toUpperCase()}</p>

        {/* ✅ CONFIDENCE IS ALREADY A % */}
        <p><b>Confidence:</b> {report.confidence}%</p>

        <h4>🧠 Reasoning</h4>
        <ul>
          {(report.reasons || []).map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>

        <div
          style={{
            ...styles.decision,
            background: decisionColor[decision],
          }}
        >
          FINAL DECISION: {decision}
        </div>
      </div>
    </div>
  );
}

/* ---------------- STYLES ---------------- */

const styles = {
  container: {
    marginTop: 30,
    padding: 20,
    background: "#f4f6f8",
    borderRadius: 12,
  },
  card: {
    background: "#fff",
    padding: 20,
    borderRadius: 12,
    boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
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
