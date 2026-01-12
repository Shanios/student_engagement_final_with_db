import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { Download, Mail, Trash2, Eye, Clock, Users, TrendingUp, AlertCircle, CheckCircle, Loader } from "lucide-react";
import "./SessionList.css";
import "../styles/global.css";

export default function SessionList() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedSession, setSelectedSession] = useState(null);
  const [participants, setParticipants] = useState([]);
  
  const [downloadingCsv, setDownloadingCsv] = useState(new Set());
  const [sendingEmail, setSendingEmail] = useState(new Set());
  const [emailSent, setEmailSent] = useState(new Set());
  const [filterSubject, setFilterSubject] = useState("all");

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
      setDownloadingCsv((prev) => {
        const newSet = new Set(prev);
        newSet.delete(sessionId);
        return newSet;
      });
    }
  };

  // Send email with attendance
  const handleSendEmail = async (sessionId) => {
    setSendingEmail((prev) => new Set([...prev, sessionId]));

    try {
      const token = localStorage.getItem("token");
      
      const res = await axios.post(
        `http://127.0.0.1:8000/api/attendance/session/${sessionId}/send-email`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );

      console.log("✅ Email sent:", res.data);
      
      setEmailSent((prev) => new Set([...prev, sessionId]));

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

      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    } catch (err) {
      setError("Failed to delete session");
    }
  };

  // Filter sessions by subject
  const filteredSessions = filterSubject === "all" 
    ? sessions 
    : sessions.filter(s => s.subject === filterSubject);

  const uniqueSubjects = [...new Set(sessions.map(s => s.subject).filter(Boolean))];

  if (loading) {
    return (
      <div className="session-loading">
        <div className="loading-spinner">
          <Loader size={48} />
        </div>
        <p>Loading sessions...</p>
      </div>
    );
  }

  return (
    <div className="session-list-container">
      {/* Header Section */}
      <div className="session-header">
        <div className="header-content">
          <h1 className="session-title">Session History</h1>
          <p className="session-subtitle">Manage and analyze your teaching sessions</p>
        </div>
        <div className="header-stats">
          <div className="stat-card">
            <div className="stat-icon">📊</div>
            <div className="stat-info">
              <p className="stat-label">Total Sessions</p>
              <p className="stat-value">{sessions.length}</p>
            </div>
          </div>
          
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          <AlertCircle size={20} />
          <span>{error}</span>
          <button onClick={() => setError("")}>×</button>
        </div>
      )}

      {/* Filters */}
      {uniqueSubjects.length > 0 && (
        <div className="filter-section">
          <label>Filter by Subject:</label>
          <div className="filter-buttons">
            <button
              className={`filter-btn ${filterSubject === 'all' ? 'active' : ''}`}
              onClick={() => setFilterSubject('all')}
            >
              All
            </button>
            {uniqueSubjects.map(subject => (
              <button
                key={subject}
                className={`filter-btn ${filterSubject === subject ? 'active' : ''}`}
                onClick={() => setFilterSubject(subject)}
              >
                {subject}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Sessions Grid */}
      {filteredSessions.length > 0 ? (
        <div className="sessions-grid">
          {filteredSessions.map((session) => (
            <div key={session.id} className="session-card-wrapper">
              {/* Success Banner */}
              {emailSent.has(session.id) && (
                <div className="success-banner">
                  <CheckCircle size={18} />
                  <span>Attendance report sent to your email!</span>
                </div>
              )}

              <div className="session-card">
                {/* Card Header */}
                <div className="card-header">
                  <div className="header-info">
                    <h3 className="session-name">{session.title}</h3>
                    {session.subject && (
                      <span className="subject-badge">{session.subject}</span>
                    )}
                  </div>
                  <div className="engagement-score">
                    <span className="score-label">Engagement</span>
                    <span className="score-value">{(session.avg_engagement * 100).toFixed(0)}%</span>
                  </div>
                </div>

                {/* Card Details */}
                <div className="card-details">
                  <div className="detail-item">
                    <Clock size={16} />
                    <div>
                      <p className="detail-label">Date & Time</p>
                     <p className="detail-value">
  {new Date(session.ended_at + "Z").toLocaleDateString()} •
  {new Date(session.ended_at + "Z").toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  })}
</p>
                    </div>
                  </div>

                  <div className="detail-item">
                    <TrendingUp size={16} />
                    <div>
                      <p className="detail-label">Duration</p>
                      <p className="detail-value">{Math.floor(session.duration_seconds / 60)} minutes</p>
                    </div>
                  </div>

                  <div className="detail-item">
                    <Users size={16} />
                    <div>
                      <p className="detail-label">Attendees</p>
                      <p className="detail-value">{session.attendance_count} students</p>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="card-actions">
                  <button
                    className="action-btn btn-report"
                    onClick={() => navigate(`/teacher/sessions/${session.id}/report`)}
                    title="View detailed report"
                  >
                    <Eye size={16} />
                    <span>Report</span>
                  </button>
                  
                  <button
                    className="action-btn btn-download"
                    onClick={() => handleDownloadCsv(session.id)}
                    disabled={downloadingCsv.has(session.id)}
                    title="Download attendance CSV"
                  >
                    {downloadingCsv.has(session.id) ? (
                      <>
                        <Loader size={16} className="spinner" />
                        <span>Downloading...</span>
                      </>
                    ) : (
                      <>
                        <Download size={16} />
                        <span>CSV</span>
                      </>
                    )}
                  </button>

                  <button
                    className="action-btn btn-email"
                    onClick={() => handleSendEmail(session.id)}
                    disabled={sendingEmail.has(session.id)}
                    title="Send attendance report via email"
                  >
                    {sendingEmail.has(session.id) ? (
                      <>
                        <Loader size={16} className="spinner" />
                        <span>Sending...</span>
                      </>
                    ) : (
                      <>
                        <Mail size={16} />
                        <span>Email</span>
                      </>
                    )}
                  </button>

                  <button
                    className="action-btn btn-delete"
                    onClick={() => handleDeleteSession(session.id)}
                    title="Delete this session"
                  >
                    <Trash2 size={16} />
                    <span>Delete</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-icon">📭</div>
          <h3>No sessions found</h3>
          <p>
            {filterSubject !== 'all' 
              ? `No sessions for "${filterSubject}". Try a different filter.`
              : "Start a session to get attendance reports!"}
          </p>
        </div>
      )}

      {/* Attendance Details Modal */}
      {selectedSession && participants.length > 0 && (
        <div className="modal-overlay" onClick={() => { setSelectedSession(null); setParticipants([]); }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📋 Attendance Details</h2>
              <button
                className="modal-close"
                onClick={() => { setSelectedSession(null); setParticipants([]); }}
                title="Close"
              >
                ✕
              </button>
            </div>

            <div className="modal-stats">
              <div className="stat">
                <p className="stat-title">Total Attendees</p>
                <p className="stat-number">{participants.length}</p>
              </div>
              <div className="stat">
                <p className="stat-title">Avg Duration</p>
                <p className="stat-number">
                  {Math.round(
                    participants.reduce((sum, p) => sum + (p.duration_seconds || 0), 0) /
                      participants.length /
                      60
                  )} min
                </p>
              </div>
            </div>

            <div className="modal-table-wrapper">
              <table className="modal-table">
                <thead>
                  <tr>
                    <th>Student ID</th>
                    <th>Status</th>
                    <th>Joined At</th>
                    <th>Left At</th>
                    <th>Duration (min)</th>
                  </tr>
                </thead>
                <tbody>
                  {participants.map((p, idx) => (
                    <tr key={idx} className={idx % 2 === 0 ? 'even' : 'odd'}>
                      <td>👤 {p.user_id}</td>
                      <td>
                        <span className={`status-badge ${p.status}`}>
                          {p.status === "joined" ? "🟢 Joined" : "⚫ Left"}
                        </span>
                      </td>
                     <td>
  {new Date(p.joined_at + "Z").toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  })}
</td>

                      <td>
  {p.left_at
    ? new Date(p.left_at + "Z").toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit'
      })
    : "-"}
</td>

                      <td>{p.duration_seconds ? Math.round(p.duration_seconds / 60) : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button className="modal-close-btn" onClick={() => { setSelectedSession(null); setParticipants([]); }}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}