// src/pages/QuestionPapersPage.jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "./QuestionPapers.css";
const API_BASE = "http://127.0.0.1:8000";

// Same helper we used earlier in notes/login
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

export default function QuestionPapersPage() {
  const navigate = useNavigate();

  const [role, setRole] = useState("student");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const [papers, setPapers] = useState([]);

  // Filters
  const [filterSubject, setFilterSubject] = useState("");
  const [filterYear, setFilterYear] = useState("");
  const [filterExamType, setFilterExamType] = useState("");

  // Upload form
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [examType, setExamType] = useState("");
  const [year, setYear] = useState("");
  const [file, setFile] = useState(null);

  // --- Auth check and initial load ---
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

    if (payload.role) {
      setRole(payload.role);
    }

    loadPapers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadPapers(params = {}) {
    setLoading(true);
    setError("");
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        navigate("/login");
        return;
      }

      const res = await axios.get(`${API_BASE}/api/qpapers/`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        params: {
          subject: params.subject ?? (filterSubject || undefined),
          year: params.year ?? (filterYear || undefined),
          exam_type: params.exam_type ?? (filterExamType || undefined),
        },
      });

      setPapers(res.data || []);
    } catch (err) {
      console.error(err);
      setError("Failed to load question papers");
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
      formData.append("exam_type", examType);
      if (year) formData.append("year", year);
      formData.append("file", file);

      await axios.post(`${API_BASE}/api/qpapers/upload`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      // Clear form and refresh list
      setTitle("");
      setSubject("");
      setExamType("");
      setYear("");
      setFile(null);
      await loadPapers();
    } catch (err) {
      console.error(err);
      const msg =
        err.response?.data?.detail || "Failed to upload question paper";
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

      const res = await axios.get(`${API_BASE}/api/qpapers/${id}/download`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        responseType: "blob",
      });

      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);

      let filename = "question-paper.pdf";
      const disposition = res.headers["content-disposition"];
      if (disposition) {
        const match = disposition.match(/filename="?(.+)"?/);
        if (match && match[1]) {
          filename = match[1];
        }
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
    <div className="qp-page">
      {/* Top bar */}
      <header className="qp-header">
        <div className="qp-header-left">
          <h1>Question Papers</h1>
          <p className="qp-subtitle">
            Browse and download previous papers. <span>Role: {role}</span>
          </p>
        </div>
        <div className="qp-header-right">
          <button className="qp-nav-btn" onClick={() => navigate("/home")}>
            Home
          </button>
          <button className="qp-nav-btn" onClick={() => navigate("/notes")}>
            Notes
          </button>
          <button className="qp-nav-btn qp-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      {/* Error banner */}
      {error && <div className="qp-error-banner">{error}</div>}

      <div className="qp-main-grid">
        {/* LEFT SIDE: upload + filters */}
        <div className="qp-left-column">
          {role === "teacher" && (
            <section className="qp-card">
              <h2 className="qp-card-title">Upload Question Paper</h2>
              <form className="qp-form" onSubmit={handleUpload}>
                <div className="qp-form-group">
                  <label>Title</label>
                  <input
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Cloud Computing Unit Test – 1"
                  />
                </div>

                <div className="qp-form-group">
                  <label>Subject</label>
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="Cloud Computing"
                  />
                </div>

                <div className="qp-form-group">
                  <label>Exam Type</label>
                  <input
                    type="text"
                    value={examType}
                    onChange={(e) => setExamType(e.target.value)}
                    placeholder="university / internal / lab_exam"
                  />
                </div>

                <div className="qp-form-group">
                  <label>Year</label>
                  <input
                    type="number"
                    value={year}
                    onChange={(e) => setYear(e.target.value)}
                    placeholder="2024"
                  />
                </div>

                <div className="qp-form-group">
                  <label>PDF File</label>
                  <input
                    type="file"
                    accept="application/pdf"
                    onChange={(e) => setFile(e.target.files[0] || null)}
                  />
                </div>

                <button
                  className="qp-primary-btn"
                  type="submit"
                  disabled={uploading}
                >
                  {uploading ? "Uploading..." : "Upload Paper"}
                </button>
              </form>
            </section>
          )}

          <section className="qp-card">
            <h2 className="qp-card-title">Filter Papers</h2>
            <div className="qp-form">
              <div className="qp-form-group">
                <label>Subject</label>
                <input
                  type="text"
                  value={filterSubject}
                  onChange={(e) => setFilterSubject(e.target.value)}
                  placeholder="cloud, dsa, etc."
                />
              </div>

              <div className="qp-form-group">
                <label>Year</label>
                <input
                  type="number"
                  value={filterYear}
                  onChange={(e) => setFilterYear(e.target.value)}
                  placeholder="2024"
                />
              </div>

              <div className="qp-form-group">
                <label>Exam Type</label>
                <input
                  type="text"
                  value={filterExamType}
                  onChange={(e) => setFilterExamType(e.target.value)}
                  placeholder="university / internal / lab_exam"
                />
              </div>

              <button
                className="qp-secondary-btn"
                onClick={() => loadPapers()}
                disabled={loading}
              >
                {loading ? "Loading..." : "Apply Filters"}
              </button>
            </div>
          </section>
        </div>

        {/* RIGHT SIDE: list */}
        <section className="qp-card qp-list-card">
          <div className="qp-list-header">
            <h2 className="qp-card-title">Available Question Papers</h2>
            <span className="qp-count-badge">{papers.length}</span>
          </div>

          {loading && <p className="qp-muted">Loading...</p>}
          {!loading && papers.length === 0 && (
            <p className="qp-muted">No question papers found.</p>
          )}

          <ul className="qp-list">
            {papers.map((qp) => (
              <li key={qp.id} className="qp-list-item">
                <div className="qp-list-meta">
                  <h3>{qp.title}</h3>
                  <div className="qp-list-tags">
                    <span className="qp-tag">
                      Subject: {qp.subject || "-"}
                    </span>
                    <span className="qp-tag">
                      Exam: {qp.exam_type || "-"}
                    </span>
                    <span className="qp-tag">Year: {qp.year || "-"}</span>
                  </div>
                </div>
                <button
                  className="qp-download-btn"
                  onClick={() => handleDownload(qp.id)}
                >
                  ⬇ Download
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
