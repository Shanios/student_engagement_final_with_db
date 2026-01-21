import React, { useState, useEffect } from "react";
import axios from "axios";
import RealTimeEngagement from "./RealTimeEngagement";
import SessionAnalytics from "../components/SessionAnalytics";
import "../styles/global.css";
import { useNavigate } from "react-router-dom";

const API = "http://127.0.0.1:8000";

export default function TeacherDashboard() {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ending, setEnding] = useState(false);
  const [ended, setEnded] = useState(false);
  const [error, setError] = useState("");
  const [errorVisible, setErrorVisible] = useState(false);
  const [points, setPoints] = useState([]);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [elapsedTime, setElapsedTime] = useState("0:00");
  const [attendanceCount, setAttendanceCount] = useState(0);
  
  // Teacher control states
  const [roomLocked, setRoomLocked] = useState(false);
  const [studentsMuted, setStudentsMuted] = useState(false);
  const [camerasDisabled, setCamerasDisabled] = useState(false);

  // Session creation tracking
  const [sessionCreated, setSessionCreated] = useState(false);

  /* =======================
     SESSION TIMER
     ======================= */
  useEffect(() => {
    if (!sessionId || ended) return;

    const interval = setInterval(() => {
      if (sessionInfo?.started_at) {
        const startTime = new Date(sessionInfo.started_at ).getTime();
        const now = new Date().getTime();
        const elapsed = Math.floor((now - startTime) / 1000);

        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        setElapsedTime(`${minutes}:${seconds.toString().padStart(2, "0")}`);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [sessionId, ended, sessionInfo]);

  /* =======================
     AUTO-HIDE ERRORS
     ======================= */
  useEffect(() => {
    if (error) {
      setErrorVisible(true);
      const timer = setTimeout(() => setErrorVisible(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  /* =======================
     START SESSION
     ======================= */
  async function startSession() {
    setError("");
    setLoading(true);

    try {
      const token = localStorage.getItem("token");
      const res = await axios.post(
        `${API}/api/engagement/sessions`,
        { title: "Live Class Session", subject: "General" },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      console.log("🎓 Session started:", res.data.id);
      setSessionId(res.data.id);
      setSessionInfo(res.data);
      setSessionCreated(true);
      setEnded(false);
      setElapsedTime("0:00");
    } catch (err) {
      console.error("❌ Start session error:", err);
      setError(err?.response?.data?.detail || "Failed to start session");
    } finally {
      setLoading(false);
    }
  }

  /* =======================
     END SESSION
     ======================= */
  async function endSession() {
    if (!sessionId) {
      setError("❌ No active session to end");
      return;
    }

    setEnding(true);
    setError("");

    try {
      const token = localStorage.getItem("token");

      if (!token) {
        throw new Error("No authentication token found");
      }

      console.log("🛑 Sending end session request for:", sessionId);

      const res = await axios.post(
        `${API}/api/engagement/sessions/${sessionId}/end`,
        {},
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          timeout: 5000,
        }
      );

      console.log("✅ Session end response:", res.data);
      setEnded(true);
      setError("");

      console.log("📊 Redirecting to report page for session:", sessionId);

      setTimeout(() => {
        navigate(`/teacher/sessions/${sessionId}/report`, { replace: true });
      }, 1000);
    } catch (err) {
      console.error("❌ End session error:", err);

      let errorMsg = "Failed to end session";
      if (err.response?.status === 403) {
        errorMsg = "Only teachers can end sessions";
      } else if (err.response?.status === 404) {
        errorMsg = "Session not found";
      } else if (err.code === "ECONNABORTED") {
        errorMsg = "Request timeout - session may still be ended";
        setEnded(true);
        setTimeout(() => {
          navigate(`/teacher/sessions/${sessionId}/report`, { replace: true });
        }, 1000);
      } else if (err.response?.data?.detail) {
        errorMsg = err.response.data.detail;
      }

      setError(errorMsg);
    } finally {
      setEnding(false);
    }
  }

  /* =======================
     LOCK / UNLOCK ROOM
     ======================= */
  async function toggleRoomLock() {
    const token = localStorage.getItem("token");
    if (!token || !sessionId) return;

    try {
      const url = roomLocked ? "unlock" : "lock";

      await axios.post(
        `${API}/api/engagement/sessions/${sessionId}/${url}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setRoomLocked(!roomLocked);
    } catch (err) {
      console.error("Room lock error:", err);
      setError("Failed to toggle room lock");
    }
  }

  /* =======================
     MUTE ALL STUDENTS
     ======================= */
  async function muteStudents() {
    const token = localStorage.getItem("token");
    if (!token || !sessionId) return;

    try {
      await axios.post(
        `${API}/api/engagement/sessions/${sessionId}/mute`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setStudentsMuted(true);
    } catch (err) {
      console.error("Mute error:", err);
      setError("Failed to mute students");
    }
  }

  /* =======================
     DISABLE STUDENT CAMERAS
     ======================= */
  async function disableStudentCameras() {
    const token = localStorage.getItem("token");
    if (!token || !sessionId) return;

    try {
      await axios.post(
        `${API}/api/engagement/sessions/${sessionId}/disable-cameras`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setCamerasDisabled(true);
    } catch (err) {
      console.error("Camera disable error:", err);
      setError("Failed to disable cameras");
    }
  }

  /* =======================
     NAVIGATE TO VIDEO CLASS
     ======================= */
  function handleVideoClassClick() {
    if (!sessionCreated || !sessionId) {
      setError("❌ Please create an engagement session first!");
      return;
    }

    if (ended) {
      setError("❌ Session has ended. Start a new session.");
      return;
    }

    console.log("🎥 Navigating to video class for session:", sessionId);
    navigate(`/teacher/video/${sessionId}`);
  }

  /* =======================
     HEARTBEAT - DETECT REMOTE SESSION END
     ======================= */
  useEffect(() => {
    if (!sessionId || ended) return;

    const token = localStorage.getItem("token");
    const interval = setInterval(async () => {
      try {
        const res = await fetch(
          `${API}/api/engagement/sessions/${sessionId}/heartbeat`,
          {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        const data = await res.json();
        if (data.status === "ended") {
          console.log("📡 Heartbeat detected session ended");
          setEnded(true);
          setSessionCreated(false);
          clearInterval(interval);
        }
      } catch (err) {
        console.warn("⚠️ Heartbeat failed:", err);
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [sessionId, ended]);

  /* =======================
     POLL LIVE ATTENDANCE
     ======================= */
  useEffect(() => {
    if (!sessionId || ended) return;

    const token = localStorage.getItem("token");
    if (!token) return;

    const interval = setInterval(async () => {
      try {
        const res = await axios.get(
          `${API}/api/attendance/count/${sessionId}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );

        setAttendanceCount(res.data.count);
      } catch (err) {
        console.warn("Attendance poll failed", err);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [sessionId, ended]);

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
      <h1 style={{ marginBottom: "30px", color: "#f1f5f9" }}>Teacher Dashboard</h1>

      {/* Navigation Buttons */}
      <div style={{ marginBottom: "20px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
        {sessionCreated && !ended && (
          <button
            onClick={() => navigate("/teacher/sessions")}
            className="btn btn-primary"
          >
            📚 View Session History
          </button>
        )}

        {sessionCreated && !ended && (
          <button
            onClick={handleVideoClassClick}
            className="btn btn-primary"
            style={{ marginLeft: "10px", background: "#059669" }}
          >
            🎥 Start Video Class
          </button>
        )}
      </div>

      {/* Create Session Button */}
      {!sessionId && (
        <div style={{ marginTop: "40px" }}>
          <button
            onClick={startSession}
            disabled={loading}
            className="btn btn-primary"
            style={{ fontSize: "18px", padding: "14px 32px" }}
          >
            {loading && <span className="spinner"></span>}
            {loading ? "Starting..." : "🚀 Start Engagement Session"}
          </button>
        </div>
      )}

      {/* Session Active Panel */}
      {sessionId && (
        <div>
          {/* Session Info Panel */}
          <div
            style={{
              background: ended ? "#1e293b" : "#1e3a8a",
              padding: "16px",
              borderRadius: "8px",
              marginBottom: "20px",
              border: ended ? "2px solid #10b981" : "2px solid #3b82f6",
              transition: "all 0.3s ease",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "12px",
              }}
            >
              <div style={{ flex: 1 }}>
                <p style={{ margin: "0 0 8px 0", color: "#e2e8f0" }}>
                  <strong>Session ID:</strong> {sessionId}
                </p>
                <div className="session-timer" style={{ color: "#cbd5e1" }}>
                  <div style={{ marginTop: "6px", color: "#e2e8f0" }}>
                    👥 Live Attendance:{" "}
                    <strong style={{ color: "#22c55e" }}>
                      {attendanceCount}
                    </strong>
                  </div>

                  <div style={{ marginTop: "4px" }}>
                    ⏱️ Elapsed:{" "}
                    <span
                      className="session-timer-value"
                      style={{ color: "#60a5fa" }}
                    >
                      {elapsedTime}
                    </span>
                  </div>
                </div>
              </div>

              {/* Status Badge */}
              <div
                className={`status-badge ${ended ? "status-ended" : "status-live"}`}
                style={{
                  background: ended ? "#1f2937" : "#0ea5e9",
                  borderColor: ended ? "#6b7280" : "#0ea5e9",
                  color: ended ? "#9ca3af" : "#fff",
                  padding: "8px 16px",
                  borderRadius: "6px",
                  fontWeight: "bold",
                  whiteSpace: "nowrap",
                }}
              >
                {ended ? "✅ Ended" : "🔴 Live"}
              </div>
            </div>

            {/* Share Code */}
            {sessionInfo?.share_code && (
              <p style={{ margin: "0 0 12px 0", color: "#cbd5e1" }}>
                <strong>Share Code:</strong>
                <span
                  style={{
                    display: "inline-block",
                    marginLeft: "8px",
                    padding: "4px 12px",
                    background: "#1f2937",
                    border: "2px solid #3b82f6",
                    borderRadius: "4px",
                    fontSize: "16px",
                    fontFamily: "monospace",
                    fontWeight: "bold",
                    color: "#60a5fa",
                  }}
                >
                  {sessionInfo.share_code}
                </span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(sessionInfo.share_code);
                    alert("✅ Share code copied!");
                  }}
                  className="btn btn-secondary"
                  style={{
                    marginLeft: "8px",
                    background: "#1f2937",
                    borderColor: "#3b82f6",
                    color: "#60a5fa",
                  }}
                >
                  📋 Copy
                </button>
              </p>
            )}

            {/* Teacher Controls */}
            {!ended && (
              <div style={{ marginBottom: "12px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
                <button
                  onClick={toggleRoomLock}
                  className="btn btn-secondary"
                  style={{
                    background: roomLocked ? "#7c3aed" : "#3b82f6",
                  }}
                >
                  {roomLocked ? "🔓 Unlock Class" : "🔒 Lock Class"}
                </button>

                <button
                  onClick={muteStudents}
                  disabled={studentsMuted}
                  className="btn btn-secondary"
                  style={{
                    background: studentsMuted ? "#6b7280" : "#3b82f6",
                    opacity: studentsMuted ? 0.6 : 1,
                  }}
                >
                  🔇 Mute Students
                </button>

                <button
                  onClick={disableStudentCameras}
                  disabled={camerasDisabled}
                  className="btn btn-secondary"
                  style={{
                    background: camerasDisabled ? "#6b7280" : "#3b82f6",
                    opacity: camerasDisabled ? 0.6 : 1,
                  }}
                >
                  📷 Disable Cameras
                </button>
              </div>
            )}

            {/* End Session Button */}
            {!ended ? (
              <button
                onClick={endSession}
                disabled={ending || !sessionId}
                className="btn btn-danger"
                style={{
                  background: "#dc2626",
                  cursor: ending ? "not-allowed" : "pointer",
                  opacity: ending ? 0.6 : 1,
                }}
              >
                {ending && <span className="spinner"></span>}
                {ending ? "Ending..." : "🛑 End Session"}
              </button>
            ) : (
              <div
                style={{
                  padding: "12px",
                  background: "#064e3b",
                  borderRadius: "6px",
                  color: "#86efac",
                  fontWeight: "600",
                }}
              >
                ✅ Session Ended. Engagement data saved.
              </div>
            )}
          </div>

          {/* Real-time Graph */}
          
         
          {/* Analytics */}
          {/* <SessionAnalytics points={points} sessionId={sessionId} /> */}
        </div>
      )}

      {/* Error Banner */}
      {errorVisible && error && (
        <div
          style={{
            marginTop: "20px",
            padding: "14px 16px",
            background: error.includes("✅") ? "#065f46" : "#7f1d1d",
            border: error.includes("✅")
              ? "1px solid #059669"
              : "1px solid #991b1b",
            borderLeft: error.includes("✅")
              ? "4px solid #10b981"
              : "4px solid #dc2626",
            borderRadius: "6px",
            color: error.includes("✅") ? "#86efac" : "#fca5a5",
            animation: "slideIn 0.3s ease",
            display: "flex",
            alignItems: "center",
            gap: "12px",
          }}
        >
          {error}
        </div>
      )}

      <style>{`
        @keyframes slideIn {
          from {
            transform: translateY(-10px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}