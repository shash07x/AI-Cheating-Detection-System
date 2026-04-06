import React from "react";

export default function AlertPopup({ alert, onClose }) {
  if (!alert) return null;

  const colors = {
    low: "#4CAF50",
    medium: "#FF9800",
    high: "#e74c3c",
    critical: "#8e44ad",
  };

  const message = alert.reasons?.join(", ") || alert.detection_type || "Alert";
  const level = alert.violation_level || "high";

  return (
    <div style={{
      position: "fixed",
      top: 20,
      left: "50%",
      transform: "translateX(-50%)",
      background: colors[level] || "#e74c3c",
      color: "#fff",
      padding: "16px 28px",
      borderRadius: 12,
      fontSize: 18,
      fontWeight: "bold",
      zIndex: 9999,
      boxShadow: "0 6px 20px rgba(0,0,0,0.25)",
      display: "flex",
      alignItems: "center",
      gap: 12,
    }}>
      🚨 {message}
      {onClose && (
        <button
          onClick={onClose}
          style={{
            background: "rgba(255,255,255,0.3)",
            border: "none",
            color: "#fff",
            borderRadius: "50%",
            width: 28,
            height: 28,
            cursor: "pointer",
            fontSize: 14,
            fontWeight: "bold",
          }}
        >
          ✕
        </button>
      )}
    </div>
  );
}
