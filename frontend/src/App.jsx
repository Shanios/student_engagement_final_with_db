import { Routes, Route, useLocation } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import NotesPage from "./pages/NotesPage";
import Chatbot from "./pages/Chatbot";
import HomePage from "./pages/HomePage";
import QuestionPapersPage from "./pages/QuestionPapersPage";
import ChatWidget from "./components/ChatWidget";
import TeacherDashboard from "./pages/TeacherDashboard";
import ProtectedRoute from "./ProtectedRoute";
import PublicRoute from "./PublicRoute";
import StudentDashboard from "./pages/StudentDashboard";
import SessionList from "./pages/SessionList";
import SessionReplay from "./pages/SessionReplay";
import VideoClass from "./pages/VideoClass";

// ✅ NEW: Import report dashboard
import SessionReportDashboard from "./pages/SessionReportDashboard";

function App() {
  const location = useLocation();

  const hideChat =
    location.pathname === "/login" || location.pathname === "/register";

  return (
    <>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/home" element={<HomePage />} />

        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />

        <Route path="/notes" element={<ProtectedRoute><NotesPage /></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute><Chatbot /></ProtectedRoute>} />

        <Route path="/qpapers" element={<QuestionPapersPage />} />

        {/* ========== TEACHER ROUTES ========== */}
        <Route
          path="/teacher/dashboard"
          element={
            <ProtectedRoute role="teacher">
              <TeacherDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/teacher/sessions"
          element={
            <ProtectedRoute role="teacher">
              <SessionList />
            </ProtectedRoute>
          }
        />

        {/* ✅ NEW: Teacher Engagement Report Page (AFTER CLASS) */}
        <Route
          path="/teacher/sessions/:sessionId/report"
          element={
            <ProtectedRoute role="teacher">
              <SessionReportDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/teacher/sessions/:sessionId/replay"
          element={
            <ProtectedRoute role="teacher">
              <SessionReplay />
            </ProtectedRoute>
          }
        />

        {/* ✅ TEACHER VIDEO ROOM (DURING CLASS) */}
        <Route
          path="/teacher/video/:sessionId"
          element={
            <ProtectedRoute role="teacher">
              <VideoClass />
            </ProtectedRoute>
          }
        />

        {/* ========== STUDENT ROUTES ========== */}
        <Route
          path="/student/dashboard"
          element={
            <ProtectedRoute role="student">
              <StudentDashboard />
            </ProtectedRoute>
          }
        />

        {/* ✅ STUDENT VIDEO ROOM */}
        <Route
          path="/student/video/:sessionId"
          element={
            <ProtectedRoute role="student">
              <VideoClass />
            </ProtectedRoute>
          }
        />
      </Routes>

      {/* SHOW CHATWIDGET ON ALL PAGES EXCEPT LOGIN/REGISTER */}
      {!hideChat && <ChatWidget />}
    </>
  );
}

export default App;