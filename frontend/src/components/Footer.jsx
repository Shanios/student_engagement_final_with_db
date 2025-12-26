import React from "react";
import { Facebook, Linkedin, Instagram, Twitter, Youtube } from "lucide-react";


export default function UniversityFooter() {
  return (
    <footer>
      {/* TOP SECTION */}
      <div className="footer-top">

        {/* Logo + University Name */}
        <div className="footer-branding">
          <div className="footer-logo">
            <span>C</span>
          </div>

          <div className="footer-title">
            <h2>CONNECT</h2>
            <p className="footer-subtitle">CONNECT EVERYONE</p>
            <p className="footer-malayalam">BE A PERSON WHO STARVE FOR KNOWLWDGE</p>
          </div>
        </div>

        {/* Social Icons */}
        <div className="footer-social">
          <a href="https://www.facebook.com/profile.php?id=61585089864181" className="footer-icon" aria-label="Facebook">
            <Facebook size={18} />
          </a>
          <a href="#" className="footer-icon" aria-label="LinkedIn">
            <Linkedin size={18} />
          </a>
          <a href="https://www.instagram.com/connect_eduvision/" className="footer-icon" aria-label="Instagram">
            <Instagram size={18} />
          </a>
          <a href="#" className="footer-icon" aria-label="Twitter">
            <Twitter size={18} />
          </a>
          <a href="https://youtube.com/@connect-exam-solution?si=ovVrKCRw3w18jzcc" className="footer-icon" aria-label="YouTube">
            <Youtube size={18} />
          </a>
        </div>
      </div>

      {/* BOTTOM COPYRIGHT */}
      <div className="footer-copyright">
        <p>Copyright@CONNECT EDUVISION 2020</p>
      </div>
    </footer>
  );
}