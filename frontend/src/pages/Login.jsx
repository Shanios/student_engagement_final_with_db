import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { setTokens, setUser } from "../auth"; // ✅ Import centralized auth functions
import API from "../api"; // ✅ Use configured Axios instance

// 🔹 Helper to decode JWT and read the payload (role, etc.)
function parseJwt(token) {
  try {
    const base64 = token
      .split(".")[1]
      .replace(/-/g, "+")
      .replace(/_/g, "/");

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

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // ✅ UPDATED: Use API instance for better error handling
      const res = await API.post("/api/auth/login", {
        email: username,
        password,
      });

      const data = res.data; // { access_token, refresh_token, token_type, expires_in }

      // 🔹 Decode JWT to get role from payload (kept for backward compatibility)
      const payload = parseJwt(data.access_token);
      const role = payload?.role || "student";

      // ✅ NEW: Store tokens using centralized function
      setTokens(data.access_token, data.refresh_token);

      // 🔹 Save full user object with role (kept for backward compatibility)
      localStorage.setItem(
        "user",
        JSON.stringify({
          access_token: data.access_token,
          token_type: data.token_type,
          role,
        })
      );

      // optional: keep separate token if you want (kept for backward compatibility)
      localStorage.setItem("token", data.access_token);

      // ✅ NEW: Fetch and store complete user data from /me endpoint
      try {
        const userRes = await API.get("/api/auth/me");
        setUser(userRes.data); // Store { id, email, role } from backend
      } catch (meError) {
        console.warn("Failed to fetch user data from /me, using JWT payload");
        // Fallback: if /me fails, user data from JWT is already stored above
      }

      navigate("/");

    } catch (err) {
      console.error(err);
      
      // ✅ IMPROVED: Better error message extraction
      let msg = "Login failed";
      if (err.response?.data?.detail) {
        msg = err.response.data.detail;
      } else if (err.message) {
        msg = err.message;
      }
      
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="connect-login-page">
      {/* Background */}
      <div className="network-bg"></div>
      <div className="line line1"></div>
      <div className="line line2"></div>
      <div className="line line3"></div>
      <div className="line line4"></div>

      <div className="dot dot1"></div>
      <div className="dot dot2"></div>
      <div className="dot dot3"></div>
      <div className="dot dot4"></div>

      {/* Login Box */}
      <div className="login-container">
        <div className="title">
          <h2>CONNECT</h2>
          <p>Seamless Virtual Classroom</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="input-box">
            <label>Username</label>
            <input
              type="text"
              placeholder="Enter your username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div className="input-box">
            <label>Password</label>
            <div style={{ position: "relative" }}>
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPassword(prev => !prev)}
                style={{
                  position: "absolute",
                  right: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "#94a3b8",
                }}
              >
                {showPassword ? "🙈" : "👁️"}
              </button>
            </div>
          </div>

          {error && <div className="login-error">{error}</div>}

          <button className="btn" type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Sign In"}
          </button>

          <div className="extra-links">
            <p>
              <a href="#">Forgot Password?</a>
            </p>
            <p>
              New to Connect? <Link to="/register">Create Account</Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}