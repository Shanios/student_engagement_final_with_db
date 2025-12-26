import { NavLink, useNavigate } from "react-router-dom";
import "./topnav.css";
export default function MainHeader() {
  const navigate = useNavigate();

  const linkClass = ({ isActive }) =>
    "topnav-link" + (isActive ? " topnav-link-active" : "");

  const token = localStorage.getItem("token");
  const user = JSON.parse(localStorage.getItem("user"));
const role = user?.role; // "teacher" | "student"


  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  }

  return (
    <header className="topnav-root">
      {/* Left: Logo + nav links */}
      <div className="topnav-left">
        <div
          className="topnav-logo"
          onClick={() => navigate("/")}
          title="Smart Classroom"
        >
          CONNECT
          <span className="topnav-logo-sub">Classroom</span>
        </div>

        <nav className="topnav-menu">
          <NavLink to="/" className={linkClass} end>
            Home
          </NavLink>

          <div className="topnav-link-group">
            <NavLink to="/notes" className={linkClass}>
              Notes
            </NavLink>
            <span className="topnav-caret">▾</span>
          </div>

          <div className="topnav-link-group">
            <NavLink to="/qpapers" className={linkClass}>
              Exam Papers
            </NavLink>
            <span className="topnav-caret">▾</span>
          </div>

          <NavLink to="/notes" className={linkClass}>
            Upload Notes
          </NavLink>
          {role === "teacher" && (
  <>
    <NavLink to="/teacher/dashboard" className={linkClass}>
      Dashboard
    </NavLink>

    <NavLink to="/teacher/sessions" className={linkClass}>
      Sessions
    </NavLink>
    </>
   

  
)}
 {role === "student" && (
  <>
    <NavLink to="/student/dashboard" className={linkClass}>
      Dashboard
    </NavLink>

    <NavLink to="/student/dashboard" className={linkClass}>
      Join Class
    </NavLink>
  </>
)}
        </nav>
      </div>

      {/* Right */}
      <div className="topnav-right">
        {token ? (
          <button
            className="topnav-btn logout-btn"
            onClick={logout}
          >
            Logout
          </button>
        ) : (
          <button
            className="topnav-btn login-btn"
            onClick={() => navigate("/login")}
          >
            Login
          </button>
        )}
      </div>
    </header>
  );
}
