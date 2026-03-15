// src/components/ChatWidget.jsx
import { useState } from "react";
import { useLocation } from "react-router-dom";
import { useEffect } from "react";
import API from "../api/api"; // ✅ Import at top

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const location = useLocation();

  // Auto-close chatbot on page change
  useEffect(() => {
    setIsOpen(false);
    setQuestion("");
    setAnswer("");
    setError("");
  }, [location.pathname]);

  async function handleAsk() {
    if (!question.trim()) return;

    const token = localStorage.getItem("token");
    if (!token) {
      setError("Please log in to use the assistant.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // ✅ Use centralized API instance (has baseURL from env var + auto token)
      const res = await API.post("/api/chat", { question });

      setAnswer(res.data.answer || "");
    } catch (err) {
      console.error(err);

      if (err.response && err.response.status === 401) {
        setError("Session expired. Please log in again.");
      } else {
        setError("Could not get answer. Try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  function handleToggle() {
    setIsOpen((prev) => {
      const next = !prev;

      // When closing → clear input & output
      if (!next) {
        setQuestion("");
        setAnswer("");
        setError("");
      }

      return next;
    });
  }

  return (
    <>
      {/* Floating circular button */}
      <button
        type="button"
        className="chatfab-btn"
        onClick={handleToggle}
        aria-label="Open chatbot"
      >
        💬
      </button>

      {/* Slide-up panel */}
      {isOpen && (
        <div className="chatfab-panel">
          <div className="chatfab-header">
            <span>RAG Assistant</span>
            <button
              type="button"
              className="chatfab-close"
              onClick={handleToggle}
            >
              ✕
            </button>
          </div>

          <div className="chatfab-body">
            <textarea
              className="chatfab-input"
              rows={3}
              placeholder="Ask a question about your notes…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />

            <button
              type="button"
              className="chatfab-askbtn"
              onClick={handleAsk}
              disabled={loading}
            >
              {loading ? "Thinking…" : "Ask"}
            </button>

            {error && <div className="chatfab-error">{error}</div>}

            <div className="chatfab-answer">
              <div className="chatfab-answer-label">Answer:</div>
              <div className="chatfab-answer-text">
                {loading ? "…" : answer || "No answer yet."}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}