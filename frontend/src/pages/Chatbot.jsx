import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

export default function Chatbot() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  const navigate = useNavigate();

  // Redirect if not logged in
useEffect(() => {
  const token = localStorage.getItem("token");
  if (!token) navigate("/login");
}, []);


  async function askBackend() {
   const res = await axios.post(
  "http://127.0.0.1:8000/api/chat",
  { question },
  {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("token")}`,
    },
  }
);

  }

  return (
    <div style={{ padding: 20 }}>
      <h1>RAG Chatbot</h1>

      <textarea
        rows="4"
        placeholder="Ask a question"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />

      <br /><br />

      <button onClick={askBackend}>Ask</button>

      <h3>Answer:</h3>
      <p>{answer}</p>
    </div>
  );
}
