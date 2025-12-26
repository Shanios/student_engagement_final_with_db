import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("student"); // default
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false); // Added showPassword state

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          role,            // <-- IMPORTANT: send role
        }),
      });

      if (!res.ok) {
        let msg = "Registration failed";
        try {
          const data = await res.json();
          if (data.detail) {
            // detail can be array or string
            if (Array.isArray(data.detail)) {
              msg = data.detail[0]?.msg || msg;
            } else if (typeof data.detail === "string") {
              msg = data.detail;
            }
          }
        } catch {
          /* ignore JSON parse error */
        }
        throw new Error(msg);
      }

      // success
      await res.json();
      navigate("/login");
    } catch (err) {
      console.error(err);
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="connect-login-page">
      {/* Background reused from login */}
      <div className="network-bg"></div>
      <div className="line line1"></div>
      <div className="line line2"></div>
      <div className="line line3"></div>
      <div className="line line4"></div>

      <div className="dot dot1"></div>
      <div className="dot dot2"></div>
      <div className="dot dot3"></div>
      <div className="dot dot4"></div>

      <div className="login-container">
        <div className="title">
          <h2>CONNECT</h2>
          <p>Create your account</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="input-box">
            <label>Email</label>
            <input
              type="email"
              placeholder="Enter your email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="input-box">
            <label>Password</label>
            <div style={{ position: "relative" }}>
              <input
                type={showPassword ? "text" : "password"} // Dynamic type based on showPassword state
                placeholder="Choose a password"
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

          <div className="input-box">
            <label>Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              required
            >
              <option value="student">Student</option>
              <option value="teacher">Teacher</option>
            </select>
          </div>

          {error && <div className="login-error">{error}</div>}

          <button className="btn" type="submit" disabled={loading}>
            {loading ? "Registering..." : "Register"}
          </button>

          <div className="extra-links">
            <p>
              Already have an account? <Link to="/login">Login</Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}