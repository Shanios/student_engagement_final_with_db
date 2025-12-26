import { useMemo, useState, useEffect } from "react";
import axios from "axios";

export default function SessionAnalytics({ points = [], sessionId }) {
  const [advancedAnalytics, setAdvancedAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);

  // Basic analytics from points
  const analytics = useMemo(() => {
    if (!Array.isArray(points) || points.length === 0) {
      return {
        avg_score: 0,
        max_score: 0,
        min_score: 0,
        total_points: 0,
        duration_seconds: 0,
      };
    }

    const scores = points.map(p => p.score).filter(s => s !== undefined && s !== null);

    if (scores.length === 0) {
      return {
        avg_score: 0,
        max_score: 0,
        min_score: 0,
        total_points: 0,
        duration_seconds: 0,
      };
    }

    const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
    const max = Math.max(...scores);
    const min = Math.min(...scores);

    let duration = 0;
    if (points.length > 1) {
      const first = new Date(points[0].timestamp).getTime();
      const last = new Date(points[points.length - 1].timestamp).getTime();
      duration = Math.round((last - first) / 1000);
    }

    return {
      avg_score: avg.toFixed(3),
      max_score: max.toFixed(3),
      min_score: min.toFixed(3),
      total_points: scores.length,
      duration_seconds: duration,
    };
  }, [points]);

  // Fetch advanced analytics
  useEffect(() => {
    if (!sessionId) return;
    console.log("📊 Points updated:", points.length);
  console.log("First point:", points[0]);
  console.log("Last point:", points[points.length - 1]);
    setLoading(true);
    const token = localStorage.getItem("token");

    axios
      .get(`http://127.0.0.1:8000/api/engagement/sessions/${sessionId}/advanced-analytics`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((res) => {
        setAdvancedAnalytics(res.data);
      })
      .catch((err) => {
        console.error("Failed to fetch advanced analytics:", err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [sessionId]);

  // Format time
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  // Get attention color
  const getAttentionColor = (score) => {
    if (score >= 80) return "#10b981"; // Green
    if (score >= 60) return "#3b82f6"; // Blue
    if (score >= 40) return "#f59e0b"; // Amber
    return "#ef4444"; // Red
  };

  // Get attention label
  const getAttentionLabel = (score) => {
    if (score >= 80) return "Excellent";
    if (score >= 60) return "Good";
    if (score >= 40) return "Fair";
    return "Poor";
  };

  return (
    <div style={{ marginTop: 20, padding: 16, border: "1px solid #ddd", borderRadius: 8 }}>
      <h3 style={{ marginBottom: 20 }}>Session Analytics</h3>

      {/* ✅ NEW: Attention Score */}
      {advancedAnalytics && (
        <div style={{ marginBottom: 24 }}>
          <div style={{
            background: getAttentionColor(advancedAnalytics.attention_score),
            color: "#fff",
            padding: "24px",
            borderRadius: "12px",
            textAlign: "center",
            marginBottom: "20px",
          }}>
            <div style={{ fontSize: "14px", opacity: 0.9 }}>Attention Score</div>
            <div style={{ fontSize: "48px", fontWeight: "bold", marginTop: "8px" }}>
              {advancedAnalytics.attention_score}
            </div>
            <div style={{ fontSize: "14px", marginTop: "8px" }}>
              {getAttentionLabel(advancedAnalytics.attention_score)}
            </div>
          </div>

          {/* Focus Time % */}
          <div style={{ marginBottom: 16 }}>
            <strong>Focus Time:</strong>
            <div style={{ marginTop: "8px", display: "flex", alignItems: "center", gap: "8px" }}>
              <div style={{
                flex: 1,
                background: "#e5e7eb",
                borderRadius: "8px",
                height: "24px",
                overflow: "hidden",
              }}>
                <div style={{
                  background: "#3b82f6",
                  height: "100%",
                  width: `${advancedAnalytics.focus_time_percentage}%`,
                  transition: "width 0.3s ease",
                }}></div>
              </div>
              <span style={{ fontWeight: "600", minWidth: "60px" }}>
                {advancedAnalytics.focus_time_percentage}%
              </span>
            </div>
            <p style={{ fontSize: "12px", color: "#6b7280", marginTop: "4px" }}>
              Time with engagement &gt; 0.7
            </p>
          </div>

          {/* Volatility Badge */}
          <div style={{ marginBottom: 16 }}>
            <strong>Stability:</strong>
            <div style={{
              marginTop: "8px",
              display: "inline-block",
              padding: "6px 12px",
              background: advancedAnalytics.volatility < 0.2 ? "#d1fae5" : 
                          advancedAnalytics.volatility < 0.35 ? "#fef3c7" : "#fee2e2",
              color: advancedAnalytics.volatility < 0.2 ? "#065f46" : 
                     advancedAnalytics.volatility < 0.35 ? "#92400e" : "#991b1b",
              borderRadius: "6px",
              fontSize: "14px",
              fontWeight: "600",
            }}>
              {advancedAnalytics.volatility < 0.2 ? "✅ High" :
               advancedAnalytics.volatility < 0.35 ? "⚠️ Medium" : "❌ Low"}
              {" (Volatility: " + advancedAnalytics.volatility + ")"}
            </div>
          </div>

          {/* Distraction Spikes */}
          {advancedAnalytics.distraction_spikes && advancedAnalytics.distraction_spikes.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <strong>📉 Distraction Spikes: {advancedAnalytics.distraction_spikes.length}</strong>
              <div style={{ marginTop: "8px" }}>
                {advancedAnalytics.distraction_spikes.slice(0, 5).map((spike, idx) => (
                  <div key={idx} style={{
                    padding: "8px",
                    background: "#fff3cd",
                    borderLeft: "4px solid #f59e0b",
                    marginBottom: "6px",
                    borderRadius: "4px",
                    fontSize: "13px",
                  }}>
                    <span style={{ fontWeight: "600" }}>
                      {new Date(spike.timestamp).toLocaleTimeString()}
                    </span>
                    {" — Dropped "}
                    <span style={{ color: "#ef4444", fontWeight: "bold" }}>
                      {(spike.drop * 100).toFixed(0)}%
                    </span>
                    {" ("}
                    <span style={{ color: "#6b7280" }}>
                      {spike.from_score.toFixed(2)} → {spike.to_score.toFixed(2)}
                    </span>
                    {")"}
                  </div>
                ))}
                {advancedAnalytics.distraction_spikes.length > 5 && (
                  <p style={{ fontSize: "12px", color: "#6b7280", marginTop: "6px" }}>
                    +{advancedAnalytics.distraction_spikes.length - 5} more spikes
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Sustained Periods */}
          {advancedAnalytics.sustained_periods && advancedAnalytics.sustained_periods.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <strong>⏱️ Sustained Periods</strong>
              <div style={{ marginTop: "8px" }}>
                {advancedAnalytics.sustained_periods.map((period, idx) => (
                  <div key={idx} style={{
                    padding: "8px",
                    background: period.type === "high" ? "#ecfdf5" : "#fee2e2",
                    borderLeft: `4px solid ${period.type === "high" ? "#10b981" : "#ef4444"}`,
                    marginBottom: "6px",
                    borderRadius: "4px",
                    fontSize: "13px",
                  }}>
                    <span style={{ fontWeight: "600" }}>
                      {period.type === "high" ? "🟢 High Engagement" : "🔴 Low Engagement"}
                    </span>
                    {" — "}
                    <span style={{ color: "#6b7280" }}>
                      {new Date(period.start).toLocaleTimeString()} ({formatTime(period.duration_sec)})
                    </span>
                    {" — Avg: "}
                    <span style={{ fontWeight: "600", color: period.type === "high" ? "#10b981" : "#ef4444" }}>
                      {(period.avg_engagement * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {loading && <p style={{ color: "#9ca3af" }}>Loading advanced analytics...</p>}

      {/* Basic metrics grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
        <div>
          <strong>Average Engagement:</strong>
          <p style={{ margin: "8px 0 0 0", fontSize: 18, color: "#3b82f6" }}>
            {analytics.avg_score}
          </p>
        </div>
        <div>
          <strong>Max Engagement:</strong>
          <p style={{ margin: "8px 0 0 0", fontSize: 18, color: "#10b981" }}>
            {analytics.max_score}
          </p>
        </div>
        <div>
          <strong>Min Engagement:</strong>
          <p style={{ margin: "8px 0 0 0", fontSize: 18, color: "#f59e0b" }}>
            {analytics.min_score}
          </p>
        </div>
        <div>
          <strong>Total Points:</strong>
          <p style={{ margin: "8px 0 0 0", fontSize: 18, color: "#8b5cf6" }}>
            {analytics.total_points}
          </p>
        </div>
        <div>
          <strong>Duration:</strong>
          <p style={{ margin: "8px 0 0 0", fontSize: 18, color: "#ec4899" }}>
            {analytics.duration_seconds}s
          </p>
        </div>
      </div>
    </div>
  );
}