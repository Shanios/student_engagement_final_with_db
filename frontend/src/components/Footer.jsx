import React, { useState } from "react";
import { Facebook, Linkedin, Instagram, Twitter, Youtube, Mail, MapPin, Phone } from "lucide-react";
import "./Footer.css";
export default function UniversityFooter() {
  const [hoveredIcon, setHoveredIcon] = useState(null);

  const socialLinks = [
    { icon: Facebook, url: "https://www.facebook.com/profile.php?id=61585089864181", label: "Facebook", color: "facebook" },
    { icon: Linkedin, url: "#", label: "LinkedIn", color: "linkedin" },
    { icon: Instagram, url: "https://www.instagram.com/connect_eduvision/", label: "Instagram", color: "instagram" },
    { icon: Twitter, url: "#", label: "Twitter", color: "twitter" },
    { icon: Youtube, url: "https://youtube.com/@connect-exam-solution?si=ovVrKCRw3w18jzcc", label: "YouTube", color: "youtube" }
  ];

  return (
    <footer className="footer-pro">
      {/* Animated background */}
      <div className="footer-bg-animation">
        <div className="footer-glow footer-glow-1"></div>
        <div className="footer-glow footer-glow-2"></div>
      </div>

      <div className="footer-content">
        {/* TOP SECTION */}
        <div className="footer-top-pro">
          {/* Left: Branding */}
          <div className="footer-brand-section">
            <div className="footer-logo-pro">
              <div className="logo-icon">C</div>
            </div>

            <div className="footer-text-block">
              <h2 className="footer-brand-name">CONNECT</h2>
              <p className="footer-tagline">CONNECT EVERYONE</p>
              <p className="footer-mission">BE A PERSON WHO STARVES FOR KNOWLEDGE</p>
            </div>
          </div>

          {/* Center: Quick Links */}
          <div className="footer-links-section">
            <h3 className="footer-section-title">Quick Links</h3>
            <ul className="footer-links-list">
              <li><a href="#notes" className="footer-link">Study Notes</a></li>
              <li><a href="#papers" className="footer-link">Exam Papers</a></li>
              <li><a href="#syllabus" className="footer-link">Syllabus</a></li>
              <li><a href="#contact" className="footer-link">Contact Us</a></li>
            </ul>
          </div>

          {/* Right: Contact Info */}
          <div className="footer-contact-section">
            <h3 className="footer-section-title">Get in Touch</h3>
            <div className="footer-contact-item">
              <Mail size={16} className="contact-icon" />
              <span>info@connectedu.com</span>
            </div>
            <div className="footer-contact-item">
              <Phone size={16} className="contact-icon" />
              <span>+91 97776xxxxx</span>
            </div>
            <div className="footer-contact-item">
              <MapPin size={16} className="contact-icon" />
              <span>Kerala, India</span>
            </div>
          </div>

          {/* Social Icons */}
          <div className="footer-social-pro">
            <h3 className="footer-section-title">Follow Us</h3>
            <div className="footer-social-icons">
              {socialLinks.map((social, idx) => {
                const Icon = social.icon;
                return (
                  <a
                    key={idx}
                    href={social.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`footer-icon-pro ${social.color}`}
                    aria-label={social.label}
                    onMouseEnter={() => setHoveredIcon(idx)}
                    onMouseLeave={() => setHoveredIcon(null)}
                  >
                    <Icon size={20} />
                  </a>
                );
              })}
            </div>
          </div>
        </div>

        {/* DIVIDER */}
        <div className="footer-divider"></div>

        {/* BOTTOM: Copyright */}
        <div className="footer-bottom-pro">
          <p className="footer-copyright-text">
            © 2024 <span className="copyright-highlight">CONNECT EDUVISION</span>. All rights reserved.
          </p>
          <div className="footer-legal-links">
            <a href="#privacy" className="legal-link">Privacy Policy</a>
            <span className="separator">•</span>
            <a href="#terms" className="legal-link">Terms of Service</a>
            <span className="separator">•</span>
            <a href="#cookies" className="legal-link">Cookie Policy</a>
          </div>
        </div>
      </div>
    </footer>
  );
}