import React, { useEffect, useRef, useState } from "react";
import { ZegoUIKitPrebuilt } from "@zegocloud/zego-uikit-prebuilt";
import { useNavigate } from "react-router-dom";
import API from "../api/api";

const APP_ID = Number(import.meta.env.VITE_ZEGOCLOUD_APP_ID);
const SERVER_SECRET = import.meta.env.VITE_ZEGOCLOUD_SERVER_SECRET;

export default function VideoRoom({ roomId, userId, userName, userRole }) {
  const containerRef = useRef(null);
  const zpRef = useRef(null);
  const navigate = useNavigate();
  const joinedRef = useRef(false);
  const mlRetryRef = useRef(0);
  const MAX_RETRIES = 3;
  
  // State management
  const [muteStudents, setMuteStudents] = useState(false);
  const [disableCameras, setDisableCameras] = useState(false);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [ending, setEnding] = useState(false);
  const [MLActive, setMLActive] = useState(false);
  const mlStartedRef = useRef(false);
  const [mlStatus, setMlStatus] = useState("idle");
  const [currentUser, setCurrentUser] = useState(null);

  // Recording states
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);
  const [isRecording, setIsRecording] = useState(false);
  const recordingStartTimeRef = useRef(null);
  const audioContextRef = useRef(null);
  const micStreamRef = useRef(null);
  const tabStreamRef = useRef(null);

  /* =======================
     🎥 START TAB RECORDING WITH MICROPHONE
     ======================= */
  const startRecording = async () => {
    try {
      // Only teacher records
      if (userRole !== "host") return;

      console.log("🎥 Starting tab recording with microphone...");

      // 1️⃣ Get tab stream (video + tab audio)
      const tabStream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          mediaSource: "tab",
          cursor: "always",
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      tabStreamRef.current = tabStream;

      // 2️⃣ Get microphone stream (teacher's voice)
      let micStream = null;
      try {
        micStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
          video: false,
        });
        micStreamRef.current = micStream;
      } catch (err) {
        console.warn("⚠️ Microphone access denied, recording without mic", err);
      }

      // 3️⃣ Mix audio streams using Web Audio API
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioContext;

      const audioDestination = audioContext.createMediaStreamDestination();

      // Add tab audio (screen share audio)
      const tabAudioTrack = tabStream.getAudioTracks()[0];
      if (tabAudioTrack) {
        const tabAudioSource = audioContext.createMediaStreamSource(
          new MediaStream([tabAudioTrack])
        );
        tabAudioSource.connect(audioDestination);
      }

      // Add microphone audio (teacher's voice)
      if (micStream) {
        const micAudioSource = audioContext.createMediaStreamSource(micStream);
        const gainNode = audioContext.createGain();
        gainNode.gain.value = 0.8;
        micAudioSource.connect(gainNode);
        gainNode.connect(audioDestination);
      }

      // 4️⃣ Create final stream with video + mixed audio
      const finalStream = new MediaStream();

      // Add video track from tab
      const videoTrack = tabStream.getVideoTracks()[0];
      if (videoTrack) {
        finalStream.addTrack(videoTrack);
      }

      // Add mixed audio track
      const mixedAudioTrack = audioDestination.stream.getAudioTracks()[0];
      if (mixedAudioTrack) {
        finalStream.addTrack(mixedAudioTrack);
      }

      // 5️⃣ Create MediaRecorder with final stream
      const mimeType = "video/webm;codecs=vp8,opus";
      const mediaRecorder = new MediaRecorder(finalStream, { mimeType });

      mediaRecorderRef.current = mediaRecorder;
      recordedChunksRef.current = [];
      recordingStartTimeRef.current = new Date();

      // Collect video data chunks
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunksRef.current.push(event.data);
        }
      };

      // Handle recording stop
      mediaRecorder.onstop = () => {
        console.log("📹 Recording stopped, processing...");
        downloadRecording();
        cleanupRecording();
      };

      // Handle stream stop
      videoTrack?.addEventListener("ended", () => {
        console.log("🎥 User stopped tab capture");
        if (mediaRecorderRef.current?.state === "recording") {
          mediaRecorderRef.current.stop();
        }
      });

      mediaRecorder.start();
      setIsRecording(true);
      console.log("✅ Tab recording with microphone started");
    } catch (err) {
      console.error("❌ Recording error:", err);
    }
  };

  /* =======================
     🧹 CLEANUP RECORDING RESOURCES
     ======================= */
  const cleanupRecording = () => {
    console.log("🧹 Cleaning up recording resources...");

    // Stop microphone stream
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop());
      micStreamRef.current = null;
    }

    // Stop tab stream
    if (tabStreamRef.current) {
      tabStreamRef.current.getTracks().forEach((track) => track.stop());
      tabStreamRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
  };

  /* =======================
     🎥 STOP RECORDING
     ======================= */
  const stopRecording = () => {
    if (!mediaRecorderRef.current || mediaRecorderRef.current.state === "inactive") {
      console.warn("⚠️ Recording not active");
      return;
    }

    console.log("⏹️ Stopping recording...");
    mediaRecorderRef.current.stop();
    setIsRecording(false);
  };

  /* =======================
     💾 DOWNLOAD RECORDING
     ======================= */
  const downloadRecording = () => {
    if (recordedChunksRef.current.length === 0) {
      console.warn("⚠️ No recording data");
      return;
    }

    try {
      const blob = new Blob(recordedChunksRef.current, { type: "video/webm" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;

      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");
      a.download = `session_${roomId}_recording_${timestamp}.webm`;

      document.body.appendChild(a);
      a.click();

      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }, 100);

      console.log("✅ Recording downloaded:", a.download);
      recordedChunksRef.current = [];
    } catch (err) {
      console.error("❌ Download error:", err);
    }
  };

  /* =======================
     TEACHER TOGGLES
     ======================= */
  const toggleMuteStudents = async () => {
    const endpoint = muteStudents ? "unmute" : "mute";

    try {
      await API.post(
        `/api/engagement/sessions/${roomId}/${endpoint}`,
        {}
      );
      setMuteStudents(!muteStudents);
    } catch (err) {
      console.error("❌ Toggle mute error:", err);
    }
  };

  const toggleCameraStudents = async () => {
    const endpoint = disableCameras ? "enable-cameras" : "disable-cameras";

    try {
      await API.post(
        `/api/engagement/sessions/${roomId}/${endpoint}`,
        {}
      );
      setDisableCameras(!disableCameras);
    } catch (err) {
      console.error("❌ Toggle camera error:", err);
    }
  };

  /* =======================
     ML START WITH RETRY
     ======================= */
  const startMLSafely = async () => {
    if (mlStartedRef.current) return;
    mlStartedRef.current = true;

    setMlStatus("starting");

    try {
      // Ensure attendance
      await API.post(
        `/api/attendance/join/${roomId}`,
        {}
      );

      // Wait for DB commit
      await new Promise(r => setTimeout(r, 1000));

      // Start ML
      await API.post(
        `/api/engagement/start-ml?session_id=${roomId}`,
        {}
      );

      console.log("✅ ML started");
      setMlStatus("active");
      setMLActive(true);
      mlRetryRef.current = 0;

    } catch (err) {
      console.warn("⚠️ ML start failed", err);

      if (mlRetryRef.current >= MAX_RETRIES) {
        console.error("❌ ML failed permanently");
        setMlStatus("failed");
        setMLActive(false);
        return;
      }

      mlRetryRef.current += 1;
      mlStartedRef.current = false;

      setTimeout(startMLSafely, 2000);
    }
  };

  /* =======================
     END SESSION HANDLER
     ======================= */
  const handleEndSession = async () => {
    if (!roomId) {
      alert("❌ No active session");
      return;
    }

    setEnding(true);

    // Stop recording before ending
    if (isRecording) {
      console.log("🎥 Stopping recording before session end...");
      stopRecording();
      await new Promise(r => setTimeout(r, 500));
    }

    try {
      const token = localStorage.getItem("token");
      if (!token) {
        throw new Error("No authentication token found");
      }

      console.log("🛑 Teacher ending session:", roomId);

      const res = await API.post(
        `/api/engagement/sessions/${roomId}/end`,
        {},
        { timeout: 5000 }
      );

      console.log("✅ Session ended:", res.data);
      setSessionEnded(true);

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
// ✅ NEW: Fetch current user
useEffect(() => {
  const fetchUser = async () => {
    try {
      const res = await API.get("/api/auth/me");
      setCurrentUser(res.data);
    } catch (err) {
      console.error("Failed to fetch user:", err);
    }
  };
  fetchUser();
}, []);
  /* =======================
     ✅ HEARTBEAT
     ======================= */
  useEffect(() => {
    if (!roomId) return;

    const interval = setInterval(() => {
      API.post(
        `/api/engagement/sessions/${roomId}/heartbeat`,
        {}
      )
        .then(() => {
          console.log("💓 Heartbeat sent");
        })
        .catch(err => {
          console.warn("⚠️ Heartbeat error:", err.message);
        });
    }, 5000);

    return () => clearInterval(interval);
  }, [roomId]);

  /* =======================
     ML STOP ON UNMOUNT
     ======================= */
  useEffect(() => {
    return () => {
      console.log("🧹 VideoRoom unmounting");

      // Stop recording if active
      if (isRecording) {
        stopRecording();
        cleanupRecording();
      }

      // Stop ML for students
      if (userRole === "audience") {
        API.post(
          `/api/engagement/stop-ml?session_id=${roomId}`,
          {}
        ).catch(err => console.warn("ML cleanup error:", err.message));
      }
    };
  }, [roomId, userRole, isRecording]);

  /* =======================
     STUDENT ENFORCEMENT
     ======================= */
  useEffect(() => {
    if (userRole !== "audience" || !zpRef.current) return;

    const interval = setInterval(async () => {
      try {
        const res = await API.get(
          `/api/engagement/sessions/${roomId}`
        );

        res.data.mute_students
          ? zpRef.current.turnOffMicrophone()
          : zpRef.current.turnOnMicrophone();

        res.data.disable_student_cameras
          ? zpRef.current.turnOffCamera()
          : zpRef.current.turnOnCamera();
      } catch (err) {
        console.warn("Enforcement check error:", err.message);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [roomId, userRole]);

  /* =======================
     TEACHER UI SYNC
     ======================= */
  useEffect(() => {
    if (userRole !== "host") return;

    const sync = async () => {
      try {
        const res = await API.get(
          `/api/engagement/sessions/${roomId}`
        );

        setMuteStudents(res.data.mute_students);
        setDisableCameras(res.data.disable_student_cameras);
      } catch (err) {
        console.warn("Sync error:", err.message);
      }
    };

    sync();
    const interval = setInterval(sync, 3000);
    return () => clearInterval(interval);
  }, [roomId, userRole]);

  /* =======================
     SESSION END POLLING
     ======================= */
  useEffect(() => {
    if (sessionEnded) return;
    if (!roomId) return;

    const interval = setInterval(async () => {
      try {
        const res = await API.get(
          `/api/engagement/sessions/${roomId}`
        );

        if (res.data.ended_at) {
          console.log("🎯 Session ended by teacher");

          // Stop recording if still active
          if (isRecording && userRole === "host") {
            stopRecording();
            cleanupRecording();
          }

          setSessionEnded(true);

          if (userRole === "host") {
            setTimeout(() => {
              navigate(`/teacher/sessions/${roomId}/report`, { replace: true });
            }, 1000);
          } else {
            setTimeout(() => {
              navigate("/student/dashboard", { replace: true });
            }, 1000);
          }
        }
      } catch (err) {
        console.warn("Poll error:", err.message);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [roomId, userRole, sessionEnded, navigate, isRecording]);

  /* =======================
     VIDEO INITIALIZATION
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

      showMyCameraToggleButton: true,
      showMyMicrophoneToggleButton: true,
      showScreenSharingButton: isTeacher,

      showUserList: false,
      showTextChat: true,

      onJoinRoom: () => {
        joinedRef.current = true;
        console.log("✅ Zego room joined");

        // Start recording (Teacher only)
        if (userRole === "host") {
          startRecording();
        }

        // Start ML (Student only)
        if (userRole === "audience") {
          startMLSafely();
        }
      },
    });

    return () => {
      try {
        if (zpRef.current) {
          zpRef.current.destroy();
          zpRef.current = null;
        }
      } catch (err) {
        console.warn("⚠️ Error destroying Zego instance:", err);
      }
    };
  }, [roomId, userId, userName, userRole]);

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

          {/* Recording Indicator */}
          {isRecording && (
            <div
              style={{
                padding: "8px 12px",
                background: "#dc2626",
                color: "white",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: "700",
                textAlign: "center",
                animation: "pulse-red 1.5s infinite",
              }}
            >
              🎥 RECORDING (with audio)
            </div>
          )}

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

          {/* ML STATUS – FAILED */}
          {mlStatus === "failed" && (
            <div style={{
              position: "absolute",
              bottom: "20px",
              right: "20px",
              zIndex: 9999,
              background: "rgba(220, 38, 38, 0.95)",
              color: "white",
              padding: "10px 14px",
              borderRadius: "12px",
              fontSize: "12px",
              fontWeight: "600",
              maxWidth: "260px",
              textAlign: "center",
              boxShadow: "0 8px 20px rgba(0,0,0,0.25)"
            }}>
              ⚠️ AI engagement tracking failed<br />
              <span style={{ fontSize: "11px", opacity: 0.85 }}>
                Session will continue without AI analytics
              </span>
            </div>
          )}

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
{/* ML BUTTON – STUDENT ONLY */}
{userRole === "audience" && currentUser?.role === "student" && (
  <div
    style={{
      position: "absolute",
      bottom: "100px",
      right: "20px",
      zIndex: 9999,
    }}
  >
    <button
      onClick={startMLSafely}
      disabled={mlStatus === "active" || mlStatus === "starting"}
      style={{
        padding: "12px 16px",
        background: mlStatus === "active" ? "#10b981" : "#3b82f6",
        color: "white",
        border: "none",
        borderRadius: "8px",
        cursor: mlStatus === "active" ? "not-allowed" : "pointer",
        fontSize: "14px",
        fontWeight: "600",
        transition: "all 0.3s ease",
        opacity: mlStatus === "active" ? 0.8 : 1,
      }}
    >
      {mlStatus === "starting" && "⏳ Starting..."}
      {mlStatus === "active" && "🎥 ML Running"}
      {mlStatus === "idle" && "🎥 Start Engagement Tracking"}
      {mlStatus === "failed" && "❌ Start Failed"}
    </button>
  </div>
)}
      {/* ML STATUS BADGE */}
      {userRole === "audience" && mlStatus === "active" && (
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

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes pulse-red {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
      `}</style>

      <div ref={containerRef} style={{ width: "100vw", height: "100vh" }} />
    </>
  );
}
