import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import RealTimeEngagement from "./RealTimeEngagement";
import SessionAnalytics from "../components/SessionAnalytics";
import "../styles/global.css";

export default function StudentDashboard() {
  const navigate = useNavigate();
  
  const [shareCode, setShareCode] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [errorVisible, setErrorVisible] = useState(false);
  const [points, setPoints] = useState([]);

  // ✅ Auto-hide errors after 5 seconds
  React.useEffect(() => {
    if (error) {
      setErrorVisible(true);
      const timer = setTimeout(() => setErrorVisible(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  async function handleJoinSession(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const token = localStorage.getItem("token");

      if (!token) {
        throw new Error("No authentication token found");
      }

      if (!shareCode.trim()) {
        throw new Error("Please enter a share code");
      }

      console.log("📝 Joining session with code:", shareCode);

      // ✅ CRITICAL: Call backend join endpoint
      const res = await axios.post(
        "http://127.0.0.1:8000/api/engagement/sessions/join",
        { share_code: shareCode.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      console.log("✅ Join response:", res.data);

      setSessionInfo(res.data);
      setSessionId(res.data.session_id);
      setShareCode("");
      setError("");
    } catch (err) {
      const errorMsg =
        err?.response?.data?.detail || err.message || "Failed to join session";
      console.error("❌ Join error:", errorMsg);
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  }

  // ✅ NEW: Navigate to video room
  function handleStartVideoClass() {
    if (!sessionId) {
      setError("❌ Session not loaded");
      return;
    }

    console.log("🎥 Student navigating to video for session:", sessionId);
    navigate(`/student/video/${sessionId}`);
  }

  function handleLeaveSession() {
    setSessionId(null);
    setSessionInfo(null);
    setPoints([]);
    setError("");
    setShareCode("");
  }

  return (
    <div
      style={{
        padding: "20px",
        maxWidth: "1200px",
        margin: "0 auto",
        background: "#0f172a",
        minHeight: "100vh",
        color: "#e2e8f0",
      }}
    >
      <h1 style={{ marginBottom: "30px", color: "#f1f5f9" }}>Student Dashboard</h1>

      {/* 🔓 BEFORE JOINING - Show join form */}
      {!sessionId && (
        <div
          style={{
            background: "#1e293b",
            padding: "32px 24px",
            borderRadius: "8px",
            maxWidth: "400px",
            margin: "0 auto",
            border: "1px solid #334155",
            animation: "fadeIn 0.3s ease",
          }}
        >
          <h2
            style={{
              fontSize: "20px",
              marginBottom: "20px",
              textAlign: "center",
              color: "#f1f5f9",
            }}
          >
            Join a Session
          </h2>

          <form onSubmit={handleJoinSession}>
            <div style={{ marginBottom: "16px" }}>
              <label
                style={{
                  display: "block",
                  marginBottom: "8px",
                  fontWeight: "600",
                  color: "#cbd5e1",
                }}
              >
                Share Code
              </label>
              <input
                type="text"
                placeholder="Enter share code (e.g., A9F3-K2L7)"
                value={shareCode}
                onChange={(e) => setShareCode(e.target.value.toUpperCase())}
                disabled={loading}
                style={{
                  width: "100%",
                  padding: "12px",
                  fontSize: "16px",
                  border: "2px solid #334155",
                  borderRadius: "6px",
                  fontFamily: "monospace",
                  fontWeight: "bold",
                  boxSizing: "border-box",
                  backgroundColor: loading ? "#0f172a" : "#1f2937",
                  color: "#e2e8f0",
                  transition: "all 0.3s ease",
                }}
              />
              <p
                style={{
                  fontSize: "12px",
                  color: "#64748b",
                  marginTop: "4px",
                }}
              >
                Ask your teacher for the share code
              </p>
            </div>

            {errorVisible && error && (
              <div
                style={{
                  marginBottom: "16px",
                  padding: "12px",
                  background: "#7f1d1d",
                  borderRadius: "6px",
                  color: "#fca5a5",
                  fontSize: "14px",
                  border: "1px solid #991b1b",
                  animation: "slideIn 0.3s ease",
                }}
              >
                ❌ {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !shareCode.trim()}
              className="btn btn-primary"
              style={{
                width: "100%",
                fontSize: "16px",
                background:
                  loading || !shareCode.trim() ? "#334155" : "#3b82f6",
              }}
            >
              {loading && <span className="spinner"></span>}
              {loading ? "Joining..." : "👥 Join Session"}
            </button>
          </form>
        </div>
      )}

      {/* 📊 AFTER JOINING - Show session data */}
      {sessionId && sessionInfo && (
        <div>
          {/* Session Info Banner */}
          <div
            style={{
              background: "#064e3b",
              padding: "16px",
              borderRadius: "8px",
              marginBottom: "20px",
              border: "2px solid #10b981",
              animation: "slideIn 0.3s ease",
            }}
          >
            <p style={{ margin: "0 0 8px 0", color: "#d1fae5" }}>
              <strong>Session:</strong> {sessionInfo.title}
            </p>
            {sessionInfo.subject && (
              <p style={{ margin: "0 0 8px 0", color: "#d1fae5" }}>
                <strong>Subject:</strong> {sessionInfo.subject}
              </p>
            )}
            <p style={{ margin: "0 0 12px 0", color: "#d1fae5" }}>
              <strong>Started:</strong>{" "}
              {new Date(sessionInfo.started_at).toLocaleTimeString()}
            </p>

            {/* ✅ NEW: Action buttons */}
            <div style={{ display: "flex", gap: "10px" }}>
              <button
                onClick={handleStartVideoClass}
                style={{
                  padding: "10px 16px",
                  fontSize: "14px",
                  background: "#10b981",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: "600",
                }}
              >
                🎥 Start Video Class
              </button>

              <button
                onClick={handleLeaveSession}
                style={{
                  padding: "10px 16px",
                  fontSize: "14px",
                  background: "#dc2626",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: "600",
                }}
              >
                🚪 Leave Session
              </button>
            </div>
          </div>

          {/* Real-time Graph */}
          <RealTimeEngagement
            sessionId={sessionId}
            paused={false}
            onPointsUpdate={setPoints}
            mode="live"
          />

          {/* Analytics */}
          <SessionAnalytics points={points} sessionId={sessionId} />
        </div>
      )}
    </div>
  );
}