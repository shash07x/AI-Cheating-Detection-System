export default function FraudAlerts({ alerts }) {
  return (
    <div>
      <h2>Live Fraud Alerts</h2>
      {alerts.map((a, i) => (
        <div key={i} style={{ border: "1px solid red", margin: 10, padding: 10 }}>
          <p><b>Session:</b> {a.session_id}</p>
          <p><b>Final Score:</b> {a.final_score}</p>
          <p><b>Violation:</b> {a.violation_level}</p>
        </div>
      ))}
    </div>
  );
}
