import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer
} from "recharts";

export default function RiskTimelineGraph({ data }) {
  if (!data || data.length === 0) return <p>No timeline data yet</p>;

  const formatted = data.map(e => ({
    time: new Date(e.time * 1000).toLocaleTimeString(),
    score: e.final_score
  }));

  return (
    <div style={{ height: 250 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formatted}>
          <XAxis dataKey="time" />
          <YAxis domain={[0, 100]} />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#e74c3c"
            strokeWidth={3}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
