import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import VideoRoom from "../components/VideoRoom";
import API from "../api/api";

export default function VideoClass() {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          navigate("/login");
          return;
        }

        console.log("📡 Fetching session details for:", sessionId);

        // ✅ CRITICAL: Fetch full session data with role
        const res = await API.get(
          `/api/engagement/sessions/${sessionId}`
        );

        console.log("✅ Full session data:", res.data);
        console.log("✅ User role from backend:", res.data.user_role);
        console.log("✅ Room ID:", res.data.room_id);

        // 🔒 Session ended guard
        if (res.data.ended_at) {
          console.log("⚠️ Session already ended");
          navigate("/session-ended");
          return;
        }

        // ✅ CRITICAL: Validate role exists
        if (!res.data.user_role) {
          throw new Error("Backend did not return user_role");
        }

        setSession(res.data);
      } catch (err) {
        console.error("❌ Failed to load session:", err.response?.data || err.message);
        const errorMsg =
          err?.response?.data?.detail || err.message || "Failed to load session";
        setError(errorMsg);
        
        // Redirect to appropriate dashboard after delay
        setTimeout(() => {
          navigate(-1); // Go back to dashboard
        }, 2000);
      } finally {
        setLoading(false);
      }
    };

    fetchSession();
  }, [sessionId, navigate]);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          background: "#0f172a",
          color: "#e2e8f0",
        }}
      >
        <p>Loading class…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          background: "#0f172a",
          color: "#fca5a5",
          textAlign: "center",
          padding: "20px",
        }}
      >
        <div>
          <p>❌ {error}</p>
          <p style={{ fontSize: "12px", color: "#6b7280", marginTop: "10px" }}>
            Redirecting...
          </p>
        </div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  // ✅ BACKEND DECIDES ROLE — frontend just uses it
  const userRole = session.user_role; // "host" or "audience"
  const isTeacher = userRole === "host";

  console.log("🎬 VideoClass initialized:");
  console.log("  - Role:", userRole);
  console.log("  - Is Teacher:", isTeacher);
  console.log("  - Room ID:", session.room_id);
  console.log("  - User ID:", session.user_id);

  return (
    <VideoRoom
      roomId={session.room_id}
      userId={session.user_id}
      userName={isTeacher ? "Teacher" : "Student"}
      userRole={userRole}
    />
  );
}