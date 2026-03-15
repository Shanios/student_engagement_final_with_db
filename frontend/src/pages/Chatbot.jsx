import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api/api";

export default function Chatbot() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  // Redirect if not logged in
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) navigate("/login");
  }, [navigate]);

  async function askBackend() {
    if (!question.trim()) {
      setError("Please enter a question");
      return;
    }

    setLoading(true);
    setError("");
    setAnswer("");

    try {
      const res = await API.post(
        "/api/chat",
        { question }
      );

      setAnswer(res.data.answer || "No answer received");
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || "Failed to get answer");
    } finally {
      setLoading(false);
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      askBackend();
    }
  };

  return (
    <div style={{ padding: 20, maxWidth: 600, margin: "0 auto" }}>
      <h1>RAG Chatbot</h1>

      <textarea
        rows="4"
        placeholder="Ask a question..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyPress={handleKeyPress}
        style={{
          width: "100%",
          padding: "8px",
          fontSize: "14px",
          fontFamily: "Arial, sans-serif",
          borderRadius: "4px",
          border: "1px solid #ccc",
        }}
      />

      <br /><br />

      <button
        onClick={askBackend}
        disabled={loading}
        style={{
          padding: "10px 20px",
          background: loading ? "#ccc" : "#3b82f6",
          color: "white",
          border: "none",
          borderRadius: "4px",
          cursor: loading ? "not-allowed" : "pointer",
          fontSize: "14px",
          fontWeight: "600",
        }}
      >
        {loading ? "Thinking..." : "Ask"}
      </button>

      {error && (
        <div style={{
          marginTop: "12px",
          padding: "10px",
          background: "#fee2e2",
          color: "#991b1b",
          borderRadius: "4px",
          fontSize: "14px",
        }}>
          ❌ {error}
        </div>
      )}

      <h3>Answer:</h3>
      <div style={{
        padding: "12px",
        background: "#f3f4f6",
        borderRadius: "4px",
        minHeight: "60px",
        lineHeight: "1.5",
        color: answer ? "#1f2937" : "#9ca3af",
      }}>
        {loading ? "⏳ Waiting for response..." : answer || "No answer yet"}
      </div>
    </div>
  );
}