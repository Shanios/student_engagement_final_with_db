import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "../styles/global.css";

export default function SessionList() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedSession, setSelectedSession] = useState(null);
  const [participants, setParticipants] = useState([]);
  
  // ✅ FIXED: Track which sessions are downloading/sending
  const [downloadingCsv, setDownloadingCsv] = useState(new Set());
  const [sendingEmail, setSendingEmail] = useState(new Set());
  const [emailSent, setEmailSent] = useState(new Set());

  // Fetch all ended sessions
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          navigate("/login");
          return;
        }

        const res = await axios.get(
          "http://127.0.0.1:8000/api/engagement/sessions/teacher/all",
          { headers: { Authorization: `Bearer ${token}` } }
        );

        console.log("✅ Sessions loaded:", res.data);
        setSessions(res.data);
      } catch (err) {
        console.error("❌ Failed to load sessions:", err);
        setError("Failed to load sessions");
      } finally {
        setLoading(false);
      }
    };

    fetchSessions();
  }, [navigate]);

  // Fetch participants for selected session
  const handleViewAttendance = async (sessionId) => {
    try {
      const token = localStorage.getItem("token");
      const res = await axios.get(
        `http://127.0.0.1:8000/api/attendance/session/${sessionId}/participants`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      console.log("👥 Participants:", res.data);
      setSelectedSession(sessionId);
      setParticipants(res.data.participants || []);
    } catch (err) {
      console.error("❌ Failed to load participants:", err);
      setError("Failed to load attendance");
    }
  };

  // Download CSV
  const handleDownloadCsv = async (sessionId) => {
    // ✅ FIXED: Add this session to downloading set
    setDownloadingCsv((prev) => new Set([...prev, sessionId]));
    
    try {
      const token = localStorage.getItem("token");
      const response = await axios.get(
        `http://127.0.0.1:8000/api/attendance/session/${sessionId}/download`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: "blob",
        }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `session_${sessionId}_attendance.csv`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);

      console.log("✅ CSV downloaded");
    } catch (err) {
      console.error("❌ Download failed:", err);
      setError("Failed to download attendance");
    } finally {
      // ✅ FIXED: Remove this session from downloading set
      setDownloadingCsv((prev) => {
        const newSet = new Set(prev);
        newSet.delete(sessionId);
        return newSet;
      });
    }
  };

  // Send email with attendance
  const handleSendEmail = async (sessionId) => {
    // ✅ FIXED: Add this session to sending set
    setSendingEmail((prev) => new Set([...prev, sessionId]));

    try {
      const token = localStorage.getItem("token");
      
      const res = await axios.post(
        `http://127.0.0.1:8000/api/attendance/session/${sessionId}/send-email`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );

      console.log("✅ Email sent:", res.data);
      
      // ✅ FIXED: Add this session to emailSent set
      setEmailSent((prev) => new Set([...prev, sessionId]));

      // Hide success message after 5 seconds
      setTimeout(() => {
        setEmailSent((prev) => {
          const newSet = new Set(prev);
          newSet.delete(sessionId);
          return newSet;
        });
      }, 5000);
    } catch (err) {
      console.error("❌ Email send failed:", err);
      setError(err?.response?.data?.detail || "Failed to send email");
    } finally {
      // ✅ FIXED: Remove this session from sending set
      setSendingEmail((prev) => {
        const newSet = new Set(prev);
        newSet.delete(sessionId);
        return newSet;
      });
    }
  };

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm("Are you sure you want to delete this session?")) return;

    try {
      const token = localStorage.getItem("token");

      await axios.delete(
        `http://127.0.0.1:8000/api/engagement/sessions/${sessionId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Remove from UI
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    } catch (err) {
      setError("Failed to delete session");
    }
  };

  if (loading) {
    return (
      <div
        style={{
          padding: "20px",
          background: "#0f172a",
          minHeight: "100vh",
          color: "#e2e8f0",
          textAlign: "center",
        }}
      >
        <p>Loading sessions...</p>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "20px",
        maxWidth: "1400px",
        margin: "0 auto",
        background: "#0f172a",
        minHeight: "100vh",
        color: "#e2e8f0",
      }}
    >
      <h1 style={{ marginBottom: "30px", color: "#f1f5f9" }}>Session History</h1>

      {/* Error Banner */}
      {error && (
        <div
          style={{
            marginBottom: "20px",
            padding: "14px 16px",
            background: "#7f1d1d",
            border: "1px solid #991b1b",
            borderRadius: "6px",
            color: "#fca5a5",
          }}
        >
          ❌ {error}
        </div>
      )}

      {/* Sessions Grid */}
      {sessions.length > 0 ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))",
            gap: "20px",
            marginBottom: "30px",
          }}
        >
          {sessions.map((session) => (
            <div key={session.id}>
              {/* ✅ FIXED: Success Banner per session */}
              {emailSent.has(session.id) && (
                <div
                  style={{
                    marginBottom: "10px",
                    padding: "14px 16px",
                    background: "#065f46",
                    border: "1px solid #059669",
                    borderRadius: "6px",
                    color: "#86efac",
                    animation: "slideIn 0.3s ease",
                  }}
                >
                  ✅ Attendance report sent to your email!
                </div>
              )}

              <div
                style={{
                  background: "#1e293b",
                  border: "2px solid #334155",
                  borderRadius: "8px",
                  padding: "16px",
                  cursor: "pointer",
                  transition: "all 0.3s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "#3b82f6";
                  e.currentTarget.style.transform = "translateY(-4px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "#334155";
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                <h3 style={{ marginTop: 0, color: "#f1f5f9" }}>{session.title}</h3>

                {session.subject && (
                  <p style={{ margin: "8px 0", color: "#cbd5e1", fontSize: "14px" }}>
                    <strong>Subject:</strong> {session.subject}
                  </p>
                )}

                <p style={{ margin: "8px 0", color: "#cbd5e1", fontSize: "14px" }}>
                  <strong>Date:</strong>{" "}
                  {new Date(session.ended_at).toLocaleDateString()} at{" "}
                  {new Date(session.ended_at).toLocaleTimeString()}
                </p>

                <p style={{ margin: "8px 0", color: "#cbd5e1", fontSize: "14px" }}>
                  <strong>Duration:</strong>{" "}
                  {Math.floor(session.duration_seconds / 60)} minutes
                </p>

                <p style={{ margin: "8px 0", color: "#10b981", fontSize: "14px", fontWeight: "600" }}>
                  👥 Students Attended: {session.attendance_count}
                </p>

                <p style={{ margin: "8px 0", color: "#60a5fa", fontSize: "14px" }}>
                  📊 Avg Engagement: {(session.avg_engagement * 100).toFixed(1)}%
                </p>

                {/* Action Buttons */}
                <div style={{ display: "flex", gap: "10px", marginTop: "12px", flexWrap: "wrap" }}>
                  
                  <button
                    onClick={() => navigate(`/teacher/sessions/${session.id}/report`)}
                    style={{
                      padding: "8px 12px",
                      fontSize: "12px",
                      background: "#8b5cf6",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontWeight: "600",
                    }}
                    onMouseEnter={(e) => (e.target.style.background = "#7c3aed")}
                    onMouseLeave={(e) => (e.target.style.background = "#8b5cf6")}
                  >
                    📊 View Report
                  </button>
                  
                  <button
                    onClick={() => handleDownloadCsv(session.id)}
                    disabled={downloadingCsv.has(session.id)}
                    style={{
                      padding: "8px 12px",
                      fontSize: "12px",
                      background: downloadingCsv.has(session.id) ? "#334155" : "#10b981",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: downloadingCsv.has(session.id) ? "not-allowed" : "pointer",
                      fontWeight: "600",
                    }}
                  >
                    {downloadingCsv.has(session.id) ? "⏳ Downloading..." : "📥 Download CSV"}
                  </button>

                  <button
                    onClick={() => handleSendEmail(session.id)}
                    disabled={sendingEmail.has(session.id)}
                    style={{
                      padding: "8px 12px",
                      fontSize: "12px",
                      background: sendingEmail.has(session.id) ? "#334155" : "#ec4899",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: sendingEmail.has(session.id) ? "not-allowed" : "pointer",
                      fontWeight: "600",
                    }}
                  >
                    {sendingEmail.has(session.id) ? "⏳ Sending..." : "📧 Email Report"}
                  </button>

                  <button
                    onClick={() => handleDeleteSession(session.id)}
                    style={{
                      padding: "8px 12px",
                      fontSize: "12px",
                      background: "#dc2626",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontWeight: "600",
                    }}
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div
          style={{
            textAlign: "center",
            padding: "40px",
            color: "#64748b",
          }}
        >
          <p>No ended sessions yet. Start a session to get attendance reports!</p>
        </div>
      )}

      {/* Attendance Details Modal */}
      {selectedSession && participants.length > 0 && (
        <div
          style={{
            background: "#1e293b",
            border: "2px solid #3b82f6",
            borderRadius: "8px",
            padding: "24px",
            marginTop: "30px",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "20px",
            }}
          >
            <h2 style={{ color: "#f1f5f9", margin: 0 }}>
              📋 Attendance Details (Session #{selectedSession})
            </h2>
            <button
              onClick={() => {
                setSelectedSession(null);
                setParticipants([]);
              }}
              style={{
                background: "#334155",
                color: "white",
                border: "none",
                borderRadius: "4px",
                padding: "8px 12px",
                cursor: "pointer",
                fontWeight: "600",
              }}
            >
              ✕ Close
            </button>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "14px",
              }}
            >
              <thead>
                <tr style={{ background: "#0f172a", borderBottom: "2px solid #3b82f6" }}>
                  <th style={{ padding: "12px", textAlign: "left", color: "#60a5fa" }}>
                    Student ID
                  </th>
                  <th style={{ padding: "12px", textAlign: "left", color: "#60a5fa" }}>
                    Status
                  </th>
                  <th style={{ padding: "12px", textAlign: "left", color: "#60a5fa" }}>
                    Joined At
                  </th>
                  <th style={{ padding: "12px", textAlign: "left", color: "#60a5fa" }}>
                    Left At
                  </th>
                  <th style={{ padding: "12px", textAlign: "left", color: "#60a5fa" }}>
                    Duration (min)
                  </th>
                </tr>
              </thead>
              <tbody>
                {participants.map((p, idx) => (
                  <tr
                    key={idx}
                    style={{
                      borderBottom: "1px solid #334155",
                      background: idx % 2 === 0 ? "#1e293b" : "#0f172a",
                    }}
                  >
                    <td style={{ padding: "12px", color: "#e2e8f0" }}>
                      👤 {p.user_id}
                    </td>
                    <td style={{ padding: "12px" }}>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "4px 8px",
                          borderRadius: "4px",
                          fontSize: "12px",
                          fontWeight: "600",
                          background: p.status === "joined" ? "#065f46" : "#1f2937",
                          color: p.status === "joined" ? "#86efac" : "#9ca3af",
                        }}
                      >
                        {p.status === "joined" ? "🟢 Joined" : "⚫ Left"}
                      </span>
                    </td>
                    <td style={{ padding: "12px", color: "#cbd5e1" }}>
                      {new Date(p.joined_at).toLocaleTimeString()}
                    </td>
                    <td style={{ padding: "12px", color: "#cbd5e1" }}>
                      {p.left_at ? new Date(p.left_at).toLocaleTimeString() : "-"}
                    </td>
                    <td style={{ padding: "12px", color: "#cbd5e1" }}>
                      {p.duration_seconds
                        ? Math.round(p.duration_seconds / 60)
                        : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: "20px", color: "#cbd5e1" }}>
            <p>
              <strong>Total Attendees:</strong> {participants.length}
            </p>
            <p>
              <strong>Avg Duration:</strong>{" "}
              {Math.round(
                participants.reduce((sum, p) => sum + (p.duration_seconds || 0), 0) /
                  participants.length /
                  60
              )}{" "}
              minutes
            </p>
          </div>
        </div>
      )}
    </div>
  );
}