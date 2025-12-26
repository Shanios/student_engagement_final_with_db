// src/pages/HomePage.jsx
import { useNavigate } from "react-router-dom";
import "./HomePage.css";
import MainHeader from "../components/MainHeader";
import PosterCarousel from "../components/PosterCarousel"
import EngagementCapture from "../components/EngagementCapture";
import { useState } from "react";
import Footer from "../components/Footer";
import "../styles/global.css";

export default function HomePage() {
  const navigate = useNavigate();
  const [engageOn, setEngageOn] = useState(false);

  return (
    <div className="home-root" style={{
      background: "#0f172a",
      minHeight: "100vh",
      color: "#e2e8f0"
    }}>
      <MainHeader />

      {/* Alert strip */}
      <div className="home-alert-strip" style={{
        background: "#1e293b",
        borderBottom: "1px solid #334155"
      }}>
        <span className="home-alert-pill" style={{
          background: "#dc2626",
          color: "#fff"
        }}>Alerts</span>

        <div className="marquee-container">
          <div className="marquee-text" style={{
            color: "#cbd5e1"
          }}>
            Registration for internal exam is opened • 
            Timetable released for S1–S6 • 
            Revaluation application started • 
            New academic calendar published • 
          </div>
        </div>
      </div>

      <PosterCarousel />

      {/* Banner / hero */}
      <section className="home-hero" style={{
        background: "linear-gradient(135deg, #1e3a8a 0%, #1e293b 100%)",
        padding: "60px 20px",
        textAlign: "center"
      }}>
        <div className="home-hero-text">
          <p className="hero-tag" style={{
            color: "#60a5fa",
            fontSize: "14px",
            fontWeight: "600",
            marginBottom: "12px"
          }}>Exam Updates</p>
          
          <h1 style={{
            color: "#f1f5f9",
            fontSize: "42px",
            fontWeight: "bold",
            marginBottom: "16px"
          }}>Smart Classroom & Exam Prep</h1>
          
          <p className="hero-sub" style={{
            color: "#cbd5e1",
            fontSize: "18px",
            marginBottom: "24px",
            maxWidth: "600px",
            margin: "0 auto 24px"
          }}>
            Access notes, exam papers, and solved QPs – all in one place.
          </p>
          
          <button
            className="hero-cta"
            onClick={() => navigate("/notes")}
            style={{
              padding: "14px 32px",
              fontSize: "16px",
              fontWeight: "600",
              background: "#3b82f6",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              transition: "all 0.3s ease",
            }}
            onMouseEnter={(e) => e.target.style.background = "#1d4ed8"}
            onMouseLeave={(e) => e.target.style.background = "#3b82f6"}
          >
            Browse Notes
          </button>
        </div>

        <div className="home-hero-graphic" style={{
          marginTop: "40px"
        }}>
          <div className="hero-card" style={{
            background: "#1e3a8a",
            border: "2px solid #3b82f6",
            padding: "32px",
            borderRadius: "12px",
            textAlign: "center",
            color: "#e2e8f0"
          }}>
            <span className="hero-emoji" style={{
              fontSize: "48px",
              display: "block",
              marginBottom: "16px"
            }}>📚</span>
            <p style={{
              fontSize: "18px",
              margin: "0",
              color: "#cbd5e1"
            }}>Study smarter, not harder.</p>
          </div>
        </div>
      </section>

      {/* Round buttons grid */}
      <section className="home-grid" style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
        gap: "20px",
        padding: "60px 20px",
        maxWidth: "1200px",
        margin: "0 auto"
      }}>
        
        {/* NOTES */}
        <div 
          className="home-tile red"
          onClick={() => navigate("/notes")}
          style={{
            background: "linear-gradient(135deg, #7f1d1d 0%, #5f0f0f 100%)",
            padding: "40px 20px",
            borderRadius: "12px",
            textAlign: "center",
            cursor: "pointer",
            transition: "all 0.3s ease",
            border: "2px solid #dc2626",
            minHeight: "200px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "translateY(-8px)";
            e.currentTarget.style.boxShadow = "0 12px 24px rgba(220, 38, 38, 0.2)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "translateY(0)";
            e.currentTarget.style.boxShadow = "none";
          }}
        >
          <div className="tile-icon" style={{
            fontSize: "48px",
            marginBottom: "12px"
          }}>
            📒
          </div>
          <div className="tile-label" style={{
            color: "#fca5a5",
            fontWeight: "600",
            fontSize: "16px"
          }}>NOTES</div>
        </div>

        {/* SYLLABUS */}
        <div 
          className="home-tile pink"
          onClick={() => window.open("https://byjus.com/rrb-exams/rrb-syllabus/", "_blank")}
          style={{
            background: "linear-gradient(135deg, #831843 0%, #500724 100%)",
            padding: "40px 20px",
            borderRadius: "12px",
            textAlign: "center",
            cursor: "pointer",
            transition: "all 0.3s ease",
            border: "2px solid #ec4899",
            minHeight: "200px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "translateY(-8px)";
            e.currentTarget.style.boxShadow = "0 12px 24px rgba(236, 72, 153, 0.2)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "translateY(0)";
            e.currentTarget.style.boxShadow = "none";
          }}
        >
          <div className="tile-icon" style={{
            fontSize: "48px",
            marginBottom: "12px"
          }}>
            🎓
          </div>
          <div className="tile-label" style={{
            color: "#f472b6",
            fontWeight: "600",
            fontSize: "16px"
          }}>SYLLABUS</div>
        </div>

        {/* EXAM PAPERS */}
        <div 
          className="home-tile purple"
          onClick={() => navigate("/qpapers")}
          style={{
            background: "linear-gradient(135deg, #6d28d9 0%, #4c1d95 100%)",
            padding: "40px 20px",
            borderRadius: "12px",
            textAlign: "center",
            cursor: "pointer",
            transition: "all 0.3s ease",
            border: "2px solid #a855f7",
            minHeight: "200px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "translateY(-8px)";
            e.currentTarget.style.boxShadow = "0 12px 24px rgba(168, 85, 247, 0.2)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "translateY(0)";
            e.currentTarget.style.boxShadow = "none";
          }}
        >
          <div className="tile-icon" style={{
            fontSize: "48px",
            marginBottom: "12px"
          }}>
            📄
          </div>
          <div className="tile-label" style={{
            color: "#d8b4fe",
            fontWeight: "600",
            fontSize: "16px"
          }}>EXAM PAPERS</div>
        </div>

        {/* UPLOAD NOTES */}
        <div 
          className="home-tile yellow"
          onClick={() => navigate("/notes")}
          style={{
            background: "linear-gradient(135deg, #78350f 0%, #451a03 100%)",
            padding: "40px 20px",
            borderRadius: "12px",
            textAlign: "center",
            cursor: "pointer",
            transition: "all 0.3s ease",
            border: "2px solid #d97706",
            minHeight: "200px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "translateY(-8px)";
            e.currentTarget.style.boxShadow = "0 12px 24px rgba(217, 119, 6, 0.2)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "translateY(0)";
            e.currentTarget.style.boxShadow = "none";
          }}
        >
          <div className="tile-icon" style={{
            fontSize: "48px",
            marginBottom: "12px"
          }}>
            ☁️
          </div>
          <div className="tile-label" style={{
            color: "#fcd34d",
            fontWeight: "600",
            fontSize: "16px"
          }}>UPLOAD NOTES</div>
        </div>
      </section>

      {/* Camera toggle button */}
      <div style={{
        textAlign: "center",
        padding: "20px"
      }}>
       
      </div>

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