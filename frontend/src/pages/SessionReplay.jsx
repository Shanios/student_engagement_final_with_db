import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import API from "../api/api";
import RealTimeEngagement from "./RealTimeEngagement";
import SessionAnalytics from "../components/SessionAnalytics";
import "../styles/global.css";

export default function SessionReplay() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchSession();
  }, [sessionId]);

  async function fetchSession() {
    setLoading(true);
    setError("");

    try {
      const token = localStorage.getItem("token");
      
      // Fetch session info
      const sessionRes = await API.get(
        `/api/engagement/sessions/${sessionId}`
      );
      
      // Fetch all points (static data)
      const pointsRes = await API.get(
        `/api/engagement/sessions/${sessionId}/series`
      );

      setSession(sessionRes.data);
      setPoints(pointsRes.data);
    } catch (err) {
      console.error("❌ Failed to fetch session:", err);
      setError(err?.response?.data?.detail || "Failed to load session");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div style={{ padding: "20px", maxWidth: "1200px", margin: "0 auto" }}>
        <div className="loading-state">Loading session...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "20px", maxWidth: "1200px", margin: "0 auto" }}>
        <div className="error-banner">{error}</div>
        <button
          onClick={() => navigate("/teacher/sessions")}
          className="btn btn-primary"
          style={{ marginTop: "20px" }}
        >
          ← Back to Sessions
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: "20px", maxWidth: "1200px", margin: "0 auto" }}>
      <button
        onClick={() => navigate("/teacher/sessions")}
        className="btn btn-secondary"
        style={{ marginBottom: "20px" }}
      >
        ← Back to Sessions
      </button>

      <h1 style={{ marginBottom: "30px", color: "#1f2937" }}>📹 Replay: {session?.title}</h1>

      <div className="session-panel ended">
        <p style={{ margin: "0 0 8px 0" }}>
          <strong>Session:</strong> {session?.title}
        </p>
        {session?.subject && (
          <p style={{ margin: "0 0 8px 0" }}>
            <strong>Subject:</strong> {session?.subject}
          </p>
        )}
        <p style={{ margin: "0 0 8px 0" }}>
          <strong>Started:</strong> {new Date(session?.started_at).toLocaleString()}
        </p>
        <p style={{ margin: "0 0 8px 0" }}>
          <strong>Ended:</strong> {new Date(session?.ended_at).toLocaleString()}
        </p>
        <p style={{ margin: "0" }}>
          <strong>Share Code:</strong> {session?.share_code}
        </p>
      </div>

      {/* ✅ NEW: mode="replay" disables polling */}
      <RealTimeEngagement 
        sessionId={sessionId} 
        paused={false}
        mode="replay"  // ✅ STATIC MODE
        onPointsUpdate={() => {}}
      />

      <SessionAnalytics points={points} sessionId={sessionId} />
    </div>
  );
}