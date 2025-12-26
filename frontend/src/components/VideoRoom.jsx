import React, { useEffect, useRef, useState } from "react";
import { ZegoUIKitPrebuilt } from "@zegocloud/zego-uikit-prebuilt";
import axios from "axios";
import { useNavigate } from "react-router-dom";

const APP_ID = Number(import.meta.env.VITE_ZEGOCLOUD_APP_ID);
const SERVER_SECRET = import.meta.env.VITE_ZEGOCLOUD_SERVER_SECRET;
const API = "http://127.0.0.1:8000";

export default function VideoRoom({ roomId, userId, userName, userRole }) {
  const containerRef = useRef(null);
  const zpRef = useRef(null);
  const navigate = useNavigate();

  const [muteStudents, setMuteStudents] = useState(false);
  const [disableCameras, setDisableCameras] = useState(false);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [ending, setEnding] = useState(false); // ✅ NEW: Track ending state
  const [MLActive, setMLActive] = useState(false); // ✅ NEW: ML status

  /* =======================
     TEACHER TOGGLES
     ======================= */
  const toggleMuteStudents = async () => {
    const token = localStorage.getItem("token");
    const endpoint = muteStudents ? "unmute" : "mute";

    await axios.post(
      `${API}/api/engagement/sessions/${roomId}/${endpoint}`,
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );

    setMuteStudents(!muteStudents);
  };

  const toggleCameraStudents = async () => {
    const token = localStorage.getItem("token");
    const endpoint = disableCameras ? "enable-cameras" : "disable-cameras";

    await axios.post(
      `${API}/api/engagement/sessions/${roomId}/${endpoint}`,
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );

    setDisableCameras(!disableCameras);
  };

  /* =======================
     ✅ NEW: END SESSION BUTTON HANDLER
     ======================= */
  const handleEndSession = async () => {
    if (!roomId) {
      alert("❌ No active session");
      return;
    }

    setEnding(true);

    try {
      const token = localStorage.getItem("token");
      if (!token) {
        throw new Error("No authentication token found");
      }

      console.log("🛑 Teacher ending session from video:", roomId);

      const res = await axios.post(
        `${API}/api/engagement/sessions/${roomId}/end`,
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
      setSessionEnded(true);

      // ✅ Redirect to report page after 2 seconds
      setTimeout(() => {
        console.log("📊 Redirecting to report page...");
        navigate(`/teacher/sessions/${roomId}/report`, { replace: true });
      }, 2000);

    } catch (err) {
      console.error("❌ End session error:", err);
      alert("❌ Failed to end session: " + (err.response?.data?.detail || err.message));
      setEnding(false);
    }
  };

  /* =======================
     STUDENT ATTENDANCE JOIN + ML START
     ======================= */
  useEffect(() => {
    if (userRole !== "audience") return;

    const token = localStorage.getItem("token");
    
    // 1. Record attendance
    axios.post(
      `${API}/api/attendance/join/${roomId}`,
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );
    console.log("🔍 Calling ML start URL:", `${API}/api/engagement/start-ml?session_id=${roomId}`);
console.log("🔍 Session ID:", roomId);
    // 2. Start ML process (fire-and-forget)
    axios.post(
      `${API}/api/engagement/start-ml?session_id=${roomId}`,
      {},
      { 
        headers: { Authorization: `Bearer ${token}` },
        timeout: 3000 
      }
    ).then(() => {
      console.log("✅ ML started for session:", roomId);
      setMLActive(true);
    }).catch(err => {
      console.warn("⚠️ ML start failed (continuing anyway):", err.message);
      setMLActive(false);
    });
  }, [roomId, userRole]);

  /* =======================
     ML STOP ON COMPONENT UNMOUNT
     ======================= */
  useEffect(() => {
    return () => {
      console.log("🧹 VideoRoom unmounted");
      console.log("Navigating away from session:", roomId);
      
      if (userRole === "audience") {
        const token = localStorage.getItem("token");
        // Stop ML - fire and forget
        axios.post(
          `${API}/api/engagement/stop-ml?session_id=${roomId}`,
          {},
          { headers: { Authorization: `Bearer ${token}` } }
        ).catch(err => console.log("ML cleanup on unmount:", err.message));
      }
    };
  }, [roomId, userRole]);

  /* =======================
     ML STOP WHEN SESSION ENDS
     ======================= */
  useEffect(() => {
    if (sessionEnded && userRole === "audience") {
      const token = localStorage.getItem("token");
      // Stop ML - fire and forget
      axios.post(
        `${API}/api/engagement/stop-ml?session_id=${roomId}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      ).catch(err => console.log("ML cleanup on session end:", err.message));
    }
  }, [sessionEnded, userRole, roomId]);

  /* =======================
     STUDENT ENFORCEMENT
     ======================= */
  useEffect(() => {
    if (userRole !== "audience" || !zpRef.current) return;

    const token = localStorage.getItem("token");

    const interval = setInterval(async () => {
      const res = await axios.get(
        `${API}/api/engagement/sessions/${roomId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      res.data.mute_students
        ? zpRef.current.turnOffMicrophone()
        : zpRef.current.turnOnMicrophone();

      res.data.disable_student_cameras
        ? zpRef.current.turnOffCamera()
        : zpRef.current.turnOnCamera();
    }, 3000);

    return () => clearInterval(interval);
  }, [roomId, userRole]);

  /* =======================
     SYNC FLAGS FOR TEACHER UI
     ======================= */
  useEffect(() => {
    if (userRole !== "host") return;

    const token = localStorage.getItem("token");

    const sync = async () => {
      const res = await axios.get(
        `${API}/api/engagement/sessions/${roomId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setMuteStudents(res.data.mute_students);
      setDisableCameras(res.data.disable_student_cameras);
    };

    sync();
    const interval = setInterval(sync, 3000);
    return () => clearInterval(interval);
  }, [roomId, userRole]);

  /* =======================
     VIDEO INIT
     ======================= */
  useEffect(() => {
    if (!containerRef.current) return;

    const isTeacher = userRole === "host";

    const kitToken = ZegoUIKitPrebuilt.generateKitTokenForTest(
      APP_ID,
      SERVER_SECRET,
      roomId,
      userId,
      userName
    );

    const zp = ZegoUIKitPrebuilt.create(kitToken);
    zpRef.current = zp;

    zp.joinRoom({
      container: containerRef.current,
      scenario: { mode: ZegoUIKitPrebuilt.VideoConference },

      turnOnCameraWhenJoining: isTeacher,
      turnOnMicrophoneWhenJoining: isTeacher,

      showMyCameraToggleButton: isTeacher,
      showMyMicrophoneToggleButton: isTeacher,
      showScreenSharingButton: isTeacher,

      showUserList: false,
      showTextChat: true,
      onJoinRoom: () => {
        console.log("✅ Zego joined room");
      },
      onLeaveRoom: () => {
        console.log("🚨 Zego onLeaveRoom triggered");
        console.log("Role at leave:", userRole);
        console.log("Session at leave:", roomId);

        if (userRole === "host") {
          console.log("📡 Host left video → Backend will decide next action");
        } else {
          console.log("👨‍🎓 Student left video → Will check backend session state");
          setMLActive(false);
          // Stop ML when student leaves video room
          const token = localStorage.getItem("token");
          // Stop ML - fire and forget
          axios.post(
            `${API}/api/engagement/stop-ml?session_id=${roomId}`,
            {},
            { headers: { Authorization: `Bearer ${token}` } }
          ).catch(err => console.log("ML cleanup on leave:", err.message));
        }
      },
    });

    return () => {
      zp.destroy();
      zpRef.current = null;
    };
  }, [roomId, userId, userName, userRole]);

  /* =======================
     ✅ POLL SESSION END (TEACHER + STUDENT)
     ======================= */
  useEffect(() => {
    if (sessionEnded) return;

    const token = localStorage.getItem("token");
    if (!token) return;

    const interval = setInterval(async () => {
      try {
        const res = await axios.get(
          `${API}/api/engagement/sessions/${roomId}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );

        if (res.data.ended_at) {
          console.log("🎯 Backend detected session ended:", res.data.ended_at);
          setSessionEnded(true);

          if (userRole === "host") {
            console.log("📊 Redirecting teacher to report page...");
            setTimeout(() => {
              navigate(`/teacher/sessions/${roomId}/report`, { replace: true });
            }, 1000);
          } else {
            console.log("🚪 Redirecting student to dashboard...");
            setTimeout(() => {
              navigate("/student/dashboard", { replace: true });
            }, 1000);
          }
        }
      } catch (err) {
        console.warn("⚠️ Session poll error:", err.message);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [roomId, userRole, sessionEnded, navigate]);

  /* =======================
     AUTO EXIT FOR STUDENT (REDUNDANCY)
     ======================= */
  useEffect(() => {
    if (userRole !== "audience") return;

    const token = localStorage.getItem("token");
    const interval = setInterval(async () => {
      const res = await axios.get(
        `${API}/api/engagement/sessions/${roomId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (res.data.ended_at) {
        navigate("/student/dashboard", { replace: true });
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [roomId, userRole, navigate]);

  return (
    <>
      {/* 🎛️ TEACHER CONTROLS */}
      {userRole === "host" && (
        <div
          style={{
            position: "absolute",
            top: "20px",
            left: "20px",
            zIndex: 9999,
            display: "flex",
            flexDirection: "column",
            gap: "12px",
            maxWidth: "300px",
          }}
        >
          {/* Mute & Camera Buttons */}
          <div style={{ display: "flex", gap: "12px" }}>
            <button
              onClick={toggleMuteStudents}
              style={{
                padding: "8px 12px",
                background: "#374151",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "13px",
                fontWeight: "600",
              }}
            >
              {muteStudents ? "🔊 Unmute Students" : "🔇 Mute Students"}
            </button>

            <button
              onClick={toggleCameraStudents}
              style={{
                padding: "8px 12px",
                background: "#374151",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "13px",
                fontWeight: "600",
              }}
            >
              {disableCameras ? "📷 Enable Cameras" : "🚫 Disable Cameras"}
            </button>
          </div>

          {/* ✅ NEW: End Session Button */}
          <button
            onClick={handleEndSession}
            disabled={ending || sessionEnded}
            style={{
              padding: "12px 16px",
              background: ending || sessionEnded ? "#7f1d1d" : "#dc2626",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: ending || sessionEnded ? "not-allowed" : "pointer",
              fontSize: "14px",
              fontWeight: "bold",
              opacity: ending || sessionEnded ? 0.6 : 1,
              transition: "all 0.3s ease",
            }}
          >
            {ending ? "⏳ Ending Session..." : "🛑 End Session"}
          </button>

          {/* Show status message */}
          {sessionEnded && (
            <div
              style={{
                padding: "10px",
                background: "#065f46",
                color: "#86efac",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: "600",
                textAlign: "center",
              }}
            >
              ✅ Session Ended. Redirecting...
            </div>
          )}
        </div>
      )}

      {/* ✅ ML STATUS BADGE FOR STUDENTS */}
      {userRole === "audience" && MLActive && (
        <div style={{
          position: "absolute",
          bottom: "20px",
          right: "20px",
          zIndex: 9999,
          background: "rgba(16, 185, 129, 0.9)",
          color: "white",
          padding: "8px 12px",
          borderRadius: "20px",
          fontSize: "12px",
          fontWeight: "600",
          display: "flex",
          alignItems: "center",
          gap: "6px"
        }}>
          <span style={{
            width: "8px",
            height: "8px",
            background: "white",
            borderRadius: "50%",
            animation: "pulse 2s infinite"
          }}></span>
          🧠 AI Tracking Active
        </div>
      )}

      {/* ✅ PULSE ANIMATION CSS */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>

      <div ref={containerRef} style={{ width: "100vw", height: "100vh" }} />
    </>
  );
}