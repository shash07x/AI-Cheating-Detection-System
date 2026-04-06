export default function RiskMeter({ alerts }) {
  if (!alerts.length) return <p>No active risks</p>;

  const latest = alerts[0];

  return (
    <div>
      <h2>Current Risk Level</h2>
      <h3 style={{ color: latest.violation_level === "critical" ? "red" : "orange" }}>
        {latest.violation_level.toUpperCase()}
      </h3>
    </div>
  );
}
