// src/pages/HomePage.jsx
import { useNavigate } from "react-router-dom";
import "./HomePage.css";
import MainHeader from "../components/MainHeader";
import PosterCarousel from "../components/PosterCarousel"
import EngagementCapture from "../components/EngagementCapture";
import { useState, useEffect } from "react";
import Footer from "../components/Footer";
import "../styles/global.css";

export default function HomePage() {
  const navigate = useNavigate();
  const [engageOn, setEngageOn] = useState(false);
  const [scrollY, setScrollY] = useState(0);
  const [activeAlert, setActiveAlert] = useState(0);
  const [tileHover, setTileHover] = useState(null);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const alerts = [
    "🔴 Registration for internal exam is opened",
    "📅 Timetable released for S1–S6",
    "✏️ Revaluation application started",
    "📚 New academic calendar published"
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveAlert((prev) => (prev + 1) % alerts.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const tiles = [
    { id: "notes", label: "NOTES", emoji: "📒", color: "tile-red", onClick: () => navigate("/notes") },
    { id: "syllabus", label: "SYLLABUS", emoji: "🎓", color: "tile-pink", onClick: () => window.open("https://byjus.com/rrb-exams/rrb-syllabus/", "_blank") },
    { id: "papers", label: "EXAM PAPERS", emoji: "📄", color: "tile-purple", onClick: () => navigate("/qpapers") },
    { id: "upload", label: "UPLOAD NOTES", emoji: "☁️", color: "tile-amber", onClick: () => navigate("/notes") }
  ];

  return (
    <div className="home-root">
      {/* Animated background elements */}
      <div className="background-orbs">
        <div className="orb orb-1"></div>
        <div className="orb orb-2"></div>
        <div className="orb orb-3"></div>
      </div>

      <MainHeader />

      {/* Enhanced Alert Strip */}
      <div className="home-alert-strip-enhanced">
        <div className="alert-content">
          <span className="home-alert-pill-pro">ALERTS</span>
          <div className="alert-carousel">
            {alerts.map((alert, idx) => (
              <div
                key={idx}
                className={`alert-item ${idx === activeAlert ? "alert-active" : ""}`}
              >
                {alert}
              </div>
            ))}
          </div>
        </div>
      </div>

 

      {/* Hero Section - Premium */}
      <section className="home-hero-premium">
        <div className="hero-container">
          {/* Left Content */}
          <div className="hero-content">
            <div className="hero-badge">
              <span>✨ Smart Learning Platform</span>
            </div>

            <h1 className="hero-title">
              <span className="gradient-text">Master Your Exams</span>
              <span></span>
              <span className="block"> with</span>
                <span className="block"> Smart Prep</span>
            </h1>

            <p className="hero-description">
              Access comprehensive notes, past exam papers, and solved solutions all in one intelligent platform. Study smarter, ace harder.
            </p>

            <div className="hero-buttons">
              <button
                className="btn-primary"
                onClick={() => navigate("/notes")}
              >
                <span>Browse Notes</span>
                <span className="btn-arrow">→</span>
              </button>
              <button className="btn-secondary">
                Explore More
              </button>
            </div>

            {/* Stats */}
            <div className="hero-stats">
              <div className="stat">
                <p className="stat-number">10K+</p>
                <p className="stat-label">Study Materials</p>
              </div>
              <div className="stat">
                <p className="stat-number">500+</p>
                <p className="stat-label">Exam Papers</p>
              </div>
              <div className="stat">
                <p className="stat-number">50K+</p>
                <p className="stat-label">Active Users</p>
              </div>
            </div>
          </div>

          {/* Right - Animated Card */}
          <div className="hero-graphic">
            <div className="hero-card-pro">
              <div className="card-emoji">📚</div>
              <p className="card-title">Study Smarter</p>
              <p className="card-subtitle">Not Harder</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid Section */}
      <section className="home-grid-premium">
        <div className="grid-header">
          <h2>Everything You Need</h2>
          <p>Comprehensive resources designed for your academic success</p>
        </div>

        <div className="tiles-grid">
          {tiles.map((tile, idx) => (
            <div
              key={tile.id}
              className={`home-tile-pro ${tile.color}`}
              onMouseEnter={() => setTileHover(tile.id)}
              onMouseLeave={() => setTileHover(null)}
              onClick={tile.onClick}
              style={{ animationDelay: `${idx * 0.1}s` }}
            >
              <div className="tile-gradient"></div>
              <div className="tile-border"></div>
              <div className="tile-shine"></div>
              
              <div className="tile-content">
                <div className={`tile-emoji ${tileHover === tile.id ? "emoji-hover" : ""}`}>
                  {tile.emoji}
                </div>
                <h3 className="tile-label-pro">{tile.label}</h3>
                <div className="tile-underline"></div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="home-cta-section">
        <div className="cta-inner">
          <h2 className="cta-title">Ready to Transform Your Learning?</h2>
          <p className="cta-description">
            Join thousands of students who are achieving their academic goals with our comprehensive study platform.
          </p>
          <button
            className="btn-primary"
            onClick={() => navigate("/notes")}
          >
            Start Learning Now
          </button>
        </div>
      </section>

      {engageOn && (
        <EngagementCapture 
          userId={1}
          sampleFps={2}
          batchIntervalMs={5000}
        />
      )}

      <Footer />
    </div>
  );
}