// src/pages/NotesPage.jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "./NotesPage.css";

const API_BASE = "http://127.0.0.1:8000";

// Same helper as other pages
function parseJwt(token) {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    console.error("Failed to parse JWT", e);
    return null;
  }
}

export default function NotesPage() {
  const navigate = useNavigate();

  const [role, setRole] = useState("student");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const [notes, setNotes] = useState([]);

  // Filters
  const [filterSubject, setFilterSubject] = useState("");

  // Upload form
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [file, setFile] = useState(null);

  // --- Auth & initial load ---
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    const payload = parseJwt(token);
    if (!payload) {
      navigate("/login");
      return;
    }

    if (payload.role) setRole(payload.role);

    loadNotes();
  }, []);

  async function loadNotes(subjectParam) {
    setLoading(true);
    setError("");
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        navigate("/login");
        return;
      }

      const res = await axios.get(`${API_BASE}/api/notes/`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        params: {
          subject: subjectParam ?? (filterSubject || undefined),
        },
      });

      setNotes(res.data || []);
    } catch (err) {
      console.error(err);
      setError("Failed to load notes");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(e) {
    e.preventDefault();
    setError("");

    if (!file) {
      setError("Please choose a PDF file");
      return;
    }

    setUploading(true);
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        navigate("/login");
        return;
      }

      const formData = new FormData();
      formData.append("title", title);
      formData.append("subject", subject);
      formData.append("file", file);

      await axios.post(`${API_BASE}/api/notes/upload`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      setTitle("");
      setSubject("");
      setFile(null);

      await loadNotes();
    } catch (err) {
      console.error(err);
      const msg = err.response?.data?.detail || "Failed to upload note";
      setError(msg);
    } finally {
      setUploading(false);
    }
  }

  async function handleDownload(id) {
    setError("");
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        navigate("/login");
        return;
      }

      const res = await axios.get(`${API_BASE}/api/notes/${id}/download`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        responseType: "blob",
      });

      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);

      let filename = "note.pdf";
      const disposition = res.headers["content-disposition"];
      if (disposition) {
        const match = disposition.match(/filename="?(.+)"?/);
        if (match && match[1]) filename = match[1];
      }

      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      setError("Failed to download file");
    }
  }

  function handleLogout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  }

  return (
    <div className="notes-page">
      {/* Reuse CONNECT-style network background */}
      <div className="network-bg"></div>
      <div className="line line1"></div>
      <div className="line line2"></div>
      <div className="line line3"></div>
      <div className="line line4"></div>
      <div className="dot dot1"></div>
      <div className="dot dot2"></div>
      <div className="dot dot3"></div>
      <div className="dot dot4"></div>

      <div className="notes-content">
        {/* Header */}
        <header className="notes-header">
          <div>
            <h1>Notes Library</h1>
            <p className="notes-subtitle">
              Upload and access unit notes •{" "}
              <span className="notes-role-pill">
                Role: <strong>{role}</strong>
              </span>
            </p>
          </div>
          <div className="notes-header-actions">
            <button onClick={() => navigate("/")} className="notes-btn ghost">
              Home
            </button>
            <button
              onClick={() => navigate("/qpapers")}
              className="notes-btn ghost"
            >
              Question Papers
            </button>
            <button onClick={handleLogout} className="notes-btn danger">
              Logout
            </button>
          </div>
        </header>

        {error && <div className="notes-alert">{error}</div>}

        <div className="notes-layout">
          {/* LEFT: Upload + filter */}
          <div className="notes-left">
            {role === "teacher" && (
              <div className="notes-card">
                <h2 className="notes-card-title">Upload Notes (PDF)</h2>
                <form onSubmit={handleUpload} className="notes-form">
                  <div className="notes-field">
                    <label>Title</label>
                    <input
                      type="text"
                      required
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="Unit 1 – Cloud Basics"
                    />
                  </div>

                  <div className="notes-field">
                    <label>Subject</label>
                    <input
                      type="text"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      placeholder="Cloud Computing"
                    />
                  </div>

                  <div className="notes-field">
                    <label>PDF File</label>
                    <input
                      type="file"
                      accept="application/pdf"
                      onChange={(e) => setFile(e.target.files[0] || null)}
                    />
                  </div>

                  <button
                    className="notes-btn primary full"
                    type="submit"
                    disabled={uploading}
                  >
                    {uploading ? "Uploading..." : "Upload Notes"}
                  </button>
                </form>
              </div>
            )}

            <div className="notes-card">
              <h2 className="notes-card-title">Filter Notes</h2>
              <div className="notes-form">
                <div className="notes-field">
                  <label>Subject</label>
                  <input
                    type="text"
                    value={filterSubject}
                    onChange={(e) => setFilterSubject(e.target.value)}
                    placeholder="cloud, dsa, etc."
                  />
                </div>
                <button
                  className="notes-btn secondary full"
                  onClick={() => loadNotes()}
                  disabled={loading}
                >
                  {loading ? "Loading..." : "Apply Filter"}
                </button>
              </div>
            </div>
          </div>

          {/* RIGHT: List */}
          <div className="notes-right notes-card">
            <div className="notes-list-header">
              <h2 className="notes-card-title">Available Notes</h2>
              {!loading && notes.length > 0 && (
                <span className="notes-count-badge">
                  {notes.length} items
                </span>
              )}
            </div>

            {loading && <p className="notes-muted">Loading...</p>}
            {!loading && notes.length === 0 && (
              <p className="notes-muted">No notes found.</p>
            )}

            <ul className="notes-list">
              {notes.map((note) => (
                <li key={note.id} className="notes-list-item">
                  <div className="notes-list-main">
                    <div className="notes-title-row">
                      <span className="notes-title">{note.title}</span>
                    </div>
                    <div className="notes-meta">
                      <span className="notes-tag">
                        Subject: {note.subject || "-"}
                      </span>
                    </div>
                  </div>
                  <button
                    className="notes-btn small"
                    onClick={() => handleDownload(note.id)}
                  >
                    Download
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
