import { NavLink, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Menu, X, ChevronDown, LogOut } from "lucide-react";
import "./topnav.css";

export default function MainHeader() {
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notesDropdownOpen, setNotesDropdownOpen] = useState(false);
  const [examsDropdownOpen, setExamsDropdownOpen] = useState(false);

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

  const handleNavClick = () => {
    setMobileMenuOpen(false);
  };

  return (
    <header className="topnav-root">
      {/* Animated background */}
      <div className="topnav-bg-glow"></div>

      {/* Left: Logo + nav links */}
      <div className="topnav-left">
        <div
          className="topnav-logo"
          onClick={() => {
            navigate("/");
            handleNavClick();
          }}
          title="Smart Classroom"
        >
          <span className="logo-text">CONNECT</span>
          <span className="topnav-logo-sub">Classroom</span>
        </div>

        {/* Desktop Menu */}
        <nav className="topnav-menu topnav-menu-desktop">
          <NavLink to="/" className={linkClass} end>
            Home
          </NavLink>

          {/* Notes Dropdown */}
          <div 
            className="topnav-link-group"
            onMouseEnter={() => setNotesDropdownOpen(true)}
            onMouseLeave={() => setNotesDropdownOpen(false)}
          >
            <NavLink to="/notes" className={linkClass}>
              Notes
            </NavLink>
           
          </div>

          {/* Exam Papers Dropdown */}
          <div 
            className="topnav-link-group"
            onMouseEnter={() => setExamsDropdownOpen(true)}
            onMouseLeave={() => setExamsDropdownOpen(false)}
          >
            <NavLink to="/qpapers" className={linkClass}>
              Exam Papers
            </NavLink>
          
          </div>

          {/* Role-based Navigation */}
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

      {/* Right: Auth Buttons */}
      <div className="topnav-right">
        {token ? (
          <button
            className="topnav-btn logout-btn"
            onClick={logout}
            title="Logout"
          >
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        ) : (
          <button
            className="topnav-btn login-btn"
            onClick={() => navigate("/login")}
            title="Login"
          >
            Login
          </button>
        )}
      </div>

      {/* Mobile Menu Button */}
      <button
        className="topnav-mobile-toggle"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
      >
        {mobileMenuOpen ? (
          <X size={24} />
        ) : (
          <Menu size={24} />
        )}
      </button>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="topnav-mobile-menu">
          <nav className="mobile-menu-content">
            <NavLink 
              to="/" 
              className={linkClass} 
              end
              onClick={handleNavClick}
            >
              Home
            </NavLink>

            <NavLink 
              to="/notes" 
              className={linkClass}
              onClick={handleNavClick}
            >
              Notes
            </NavLink>

            <NavLink 
              to="/qpapers" 
              className={linkClass}
              onClick={handleNavClick}
            >
              Exam Papers
            </NavLink>

            {role === "teacher" && (
              <>
                <NavLink 
                  to="/teacher/dashboard" 
                  className={linkClass}
                  onClick={handleNavClick}
                >
                  Dashboard
                </NavLink>
                <NavLink 
                  to="/teacher/sessions" 
                  className={linkClass}
                  onClick={handleNavClick}
                >
                  Sessions
                </NavLink>
              </>
            )}

            {role === "student" && (
              <>
                <NavLink 
                  to="/student/dashboard" 
                  className={linkClass}
                  onClick={handleNavClick}
                >
                  Dashboard
                </NavLink>
                <NavLink 
                  to="/student/join-class" 
                  className={linkClass}
                  onClick={handleNavClick}
                >
                  Join Class
                </NavLink>
              </>
            )}

            <div className="mobile-auth-buttons">
              {token ? (
                <button
                  className="topnav-btn logout-btn"
                  onClick={() => {
                    logout();
                    handleNavClick();
                  }}
                >
                  <LogOut size={16} />
                  Logout
                </button>
              ) : (
                <button
                  className="topnav-btn login-btn"
                  onClick={() => {
                    navigate("/login");
                    handleNavClick();
                  }}
                >
                  Login
                </button>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}