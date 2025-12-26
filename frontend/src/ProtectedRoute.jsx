import { Navigate } from "react-router-dom";
import { getAuthToken, getUser, clearAuth } from "./auth";

export default function ProtectedRoute({ children, role }) {
  const token = getAuthToken(); // ✅ Uses centralized auth check
  const user = getUser();

  // 🔐 Not authenticated or token expired
  if (!token || !user) {
    clearAuth(); // ✅ Clean up any stale data
    return <Navigate to="/login" replace />;
  }

  // 🔐 Role-based protection
  if (role && user.role !== role) {
    return <Navigate to="/" replace />;
  }

  return children;
}