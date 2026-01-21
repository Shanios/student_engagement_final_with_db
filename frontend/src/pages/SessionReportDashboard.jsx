import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Download, Mail, Share2, Loader, ArrowLeft, TrendingUp, Zap, Target, Activity } from 'lucide-react';
import './SessionReport.css';

const API = 'http://127.0.0.1:8000';

export default function SessionReportDashboard() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sending, setSending] = useState(false);
  const [copied, setCopied] = useState(false);
  const [emailSuccess, setEmailSuccess] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);
  useEffect(() => {
    fetchReport();
  }, [sessionId]);

  const fetchReport = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API}/api/engagement/sessions/${sessionId}/report`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setReport(response.data);
      setError(null);
    } catch (err) {
      console.error('❌ Failed to load report:', err);
      setError(err.response?.data?.detail || 'Failed to load report');
    } finally {
      setLoading(false);
    }
  };

const downloadExcel = async () => {
  try {
    setSending(true);
    const token = localStorage.getItem('token');
    
    console.log("🔍 DEBUG - Download CSV:");
    console.log("- Session ID:", sessionId);
    console.log("- Token exists:", !!token);
    console.log("- Endpoint:", `${API}/api/attendance/session/${sessionId}/download`);
    
    const response = await axios.get(
      `${API}/api/attendance/session/${sessionId}/download`,
      { 
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }, 
        responseType: 'blob' 
      }
    );
    
    console.log("✅ Download response:", response.status, response.headers);
    
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `session_${sessionId}_attendance.csv`);
    document.body.appendChild(link);
    link.click();
    link.parentElement.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    console.log('✅ CSV downloaded successfully');
    alert('✅ Attendance CSV downloaded!');
    
  } catch (err) {
    console.error('❌ Download failed:', err);
    
    // Detailed error logging
    if (err.response) {
      console.log("📡 Response status:", err.response.status);
      console.log("📡 Response data:", err.response.data);
      console.log("📡 Response headers:", err.response.headers);
    }
    
    alert(`❌ Failed to download: ${err.message}`);
  } finally {
    setSending(false);
  }
};

const sendViaEmail = async () => {
  try {
    setSending(true);
    const token = localStorage.getItem('token');
    
    console.log("📧 DEBUG - Send Email:");
    console.log("- Session ID:", sessionId);
    console.log("- Token exists:", !!token);
    console.log("- Endpoint:", `${API}/api/attendance/session/${sessionId}/send-email`);
    
    const response = await axios.post(
      `${API}/api/attendance/session/${sessionId}/send-email`,
      {},
      { 
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        } 
      }
    );

    console.log('✅ Email response:', response.data);
    alert('✅ Engagement report sent to your email!');
    
  } catch (err) {
    console.error('❌ Email send failed:', err);
    
    // Detailed error logging
    if (err.response) {
      console.log("📡 Response status:", err.response.status);
      console.log("📡 Response data:", err.response.data);
      console.log("📡 Response headers:", err.response.headers);
    } else if (err.request) {
      console.log("📡 No response received:", err.request);
    }
    
    let errorMessage = 'Failed to send email';
    if (err.response?.status === 404) {
      errorMessage = 'Email endpoint not found (404). Check backend routes.';
    } else if (err.response?.status === 403) {
      errorMessage = 'Permission denied (403).';
    } else if (err.response?.status === 500) {
      errorMessage = 'Server error (500). Check backend logs.';
    } else if (err.code === 'ERR_NETWORK') {
      errorMessage = 'Network error. Check if backend is running.';
    } else if (err.response?.data?.detail) {
      errorMessage = err.response.data.detail;
    }
    
    alert(`❌ ${errorMessage}`);
  } finally {
    setSending(false);
  }
};

  if (loading) {
    return (
      <div className="report-loading">
        <div className="loading-container">
          <div className="loading-orb"></div>
          <div className="loading-spinner"></div>
          <p>Generating your majestic report...</p>
          <p className="loading-subtitle">This won't take long</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="report-error">
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <h2>Oops! Something went wrong</h2>
          <p>{error}</p>
          <button onClick={fetchReport} className="btn btn-primary">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="report-empty">
        <div className="empty-container">
          <div className="empty-icon">⏳</div>
          <h2>Report is being generated</h2>
          <p>Please check back in a few moments</p>
          <button onClick={fetchReport} className="btn btn-primary">
            Refresh
          </button>
        </div>
      </div>
    );
  }

  const summary = report.analytics?.summary || {};
  const distribution = report.analytics?.distribution || {};
  const critical = report.analytics?.critical_moments || {};

  const getEngagementColor = (score) => {
    if (score >= 0.67) return '#10b981';
    if (score >= 0.33) return '#f59e0b';
    return '#ef4444';
  };

  const getGrade = (score) => {
    if (score >= 0.9) return { grade: 'A+', color: '#10b981' };
    if (score >= 0.8) return { grade: 'A', color: '#10b981' };
    if (score >= 0.7) return { grade: 'B', color: '#60a5fa' };
    if (score >= 0.6) return { grade: 'C', color: '#f59e0b' };
    return { grade: 'D', color: '#ef4444' };
  };

  const gradeInfo = getGrade(summary.avg_score || 0);

  return (
    <div className="report-page">
      {/* Animated Background */}
      <div className="report-bg">
        <div className="bg-orb bg-orb-1"></div>
        <div className="bg-orb bg-orb-2"></div>
        <div className="bg-orb bg-orb-3"></div>
        <div className="bg-orb bg-orb-4"></div>
      </div>

      <div className="report-content">
        {/* Hero Header */}
        <div className="report-hero">
          <button onClick={() => navigate('/teacher/sessions')} className="back-btn">
            <ArrowLeft size={18} />
            Back to Sessions
          </button>

          <div className="hero-content">
            <h1 className="hero-title">
              <span className="title-icon">📊</span>
              Session Analytics Report
            </h1>
            <p className="hero-subtitle">
              Deep insights into student engagement and classroom performance
            </p>
          </div>

          {/* Grade Badge */}
          <div className="grade-badge" style={{ background: gradeInfo.color }}>
            <div className="grade-letter">{gradeInfo.grade}</div>
            <div className="grade-label">Overall<br/>Score</div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="action-bar">
          <button
            onClick={downloadExcel}
            disabled={sending}
            className="action-btn download-btn"
            title="Download attedance as excel"
          >
            <Download size={20} />
            <span>Download Excel</span>
            {sending && <div className="btn-spinner"></div>}
          </button>

          <button
            onClick={sendViaEmail}
            disabled={sending}
            className="action-btn email-btn"
            title="Send report via email"
          >
            <Mail size={20} />
            <span>Email Report</span>
            {sending && <div className="btn-spinner"></div>}
          </button>

          {/* <button
            onClick={() => {
              navigator.clipboard.writeText(sessionId);
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            }}
            className="action-btn share-btn"
            title="Copy session ID"
          >
            <Share2 size={20} />
            <span>{copied ? 'Copied!' : 'Share ID'}</span>
          </button> */}
        </div>

        {/* Key Metrics - Premium Cards */}
        <div className="metrics-grid">
          {/* Average Engagement */}
          <div className="metric-card engagement-card">
            <div className="metric-header">
              <h3>Average Engagement</h3>
              <Activity size={24} />
            </div>
            <div className="metric-value">
              {(summary.avg_score * 100).toFixed(1)}%
            </div>
            <div className="metric-bar">
              <div className="bar-fill" style={{
                width: `${summary.avg_score * 100}%`,
                background: getEngagementColor(summary.avg_score)
              }}></div>
            </div>
            <p className="metric-label">Overall classroom engagement level</p>
          </div>

          {/* Attention Score */}
          <div className="metric-card attention-card">
            <div className="metric-header">
              <h3>Attention Score</h3>
              <Target size={24} />
            </div>
            <div className="metric-value">
              {summary.attention_score || 0}
              <span className="metric-suffix">/100</span>
            </div>
            <div className="metric-bar">
              <div className="bar-fill" style={{
                width: `${(summary.attention_score || 0)}%`,
                background: '#a855f7'
              }}></div>
            </div>
            <p className="metric-label">Student focus and concentration</p>
          </div>

          {/* Focus Time */}
          <div className="metric-card focus-card">
            <div className="metric-header">
              <h3>Focus Time</h3>
              <Zap size={24} />
            </div>
            <div className="metric-value">
              {(summary.focus_time_percentage || 0).toFixed(1)}%
            </div>
            <div className="metric-bar">
              <div className="bar-fill" style={{
                width: `${summary.focus_time_percentage || 0}%`,
                background: '#10b981'
              }}></div>
            </div>
            <p className="metric-label">Time spent actively engaged</p>
          </div>

          {/* Duration */}
          <div className="metric-card duration-card">
            <div className="metric-header">
              <h3>Session Duration</h3>
              <TrendingUp size={24} />
            </div>
            <div className="metric-value">
              {summary.duration_formatted || '0:00'}
            </div>
            <div className="metric-subtext">
              {summary.total_points || 0} data points collected
            </div>
            <p className="metric-label">Total time recorded</p>
          </div>
        </div>

        {/* Graphs Section */}
        <div className="graphs-section">
          <h2 className="section-title">📈 Visual Analytics</h2>
          <div className="graphs-grid">
            {report.graphs?.engagement_timeline && (
              <div className="graph-card timeline-card">
                <h3>Engagement Timeline</h3>
                <img
                  src={`data:image/png;base64,${report.graphs.engagement_timeline}`}
                  alt="Engagement Timeline"
                  className="graph-image"
                />
              </div>
            )}

            {report.graphs?.distribution_chart && (
              <div className="graph-card distribution-card">
                <h3>Engagement Distribution</h3>
                <img
                  src={`data:image/png;base64,${report.graphs.distribution_chart}`}
                  alt="Distribution Chart"
                  className="graph-image"
                />
              </div>
            )}
          </div>
        </div>

        {/* Detailed Analytics */}
        <div className="analytics-section">
          <div className="analytics-grid">
            {/* Engagement Breakdown */}
            <div className="analytics-card">
              <h3>🎯 Engagement Breakdown</h3>
              <div className="breakdown-list">
                <div className="breakdown-item">
                  <div className="breakdown-label">
                    <span>High (&gt;67%)</span>
                    <span className="breakdown-value" style={{ color: '#10b981' }}>
                      {(distribution.high_engagement * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="breakdown-bar">
                    <div className="bar-fill" style={{
                      width: `${distribution.high_engagement * 100}%`,
                      background: 'linear-gradient(90deg, #10b981, #34d399)'
                    }}></div>
                  </div>
                </div>

                <div className="breakdown-item">
                  <div className="breakdown-label">
                    <span>Medium (33-67%)</span>
                    <span className="breakdown-value" style={{ color: '#f59e0b' }}>
                      {(distribution.medium_engagement * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="breakdown-bar">
                    <div className="bar-fill" style={{
                      width: `${distribution.medium_engagement * 100}%`,
                      background: 'linear-gradient(90deg, #f59e0b, #fbbf24)'
                    }}></div>
                  </div>
                </div>

                <div className="breakdown-item">
                  <div className="breakdown-label">
                    <span>Low (&lt;33%)</span>
                    <span className="breakdown-value" style={{ color: '#ef4444' }}>
                      {(distribution.low_engagement * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="breakdown-bar">
                    <div className="bar-fill" style={{
                      width: `${distribution.low_engagement * 100}%`,
                      background: 'linear-gradient(90deg, #ef4444, #f87171)'
                    }}></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Critical Moments */}
            <div className="analytics-card critical-card">
              <h3>⚡ Critical Moments</h3>
              <div className="critical-list">
                <div className="critical-item">
                  <div className="critical-icon" style={{ background: 'rgba(239, 68, 68, 0.1)' }}>
                    <span>📉</span>
                  </div>
                  <div className="critical-info">
                    <span className="critical-label">Distraction Spikes</span>
                    <span className="critical-value">{critical.total_spikes || 0}</span>
                  </div>
                </div>

                <div className="critical-item">
                  <div className="critical-icon" style={{ background: 'rgba(245, 158, 11, 0.1)' }}>
                    <span>⚠️</span>
                  </div>
                  <div className="critical-info">
                    <span className="critical-label">Engagement Dropoffs</span>
                    <span className="critical-value">{critical.total_dropoffs || 0}</span>
                  </div>
                </div>

                <div className="critical-item">
                  <div className="critical-icon" style={{ background: 'rgba(16, 185, 129, 0.1)' }}>
                    <span>📈</span>
                  </div>
                  <div className="critical-info">
                    <span className="critical-label">Peak Periods</span>
                    <span className="critical-value">{critical.total_peaks || 0}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Performance Summary */}
        <div className="performance-section">
          <h2 className="section-title">🏆 Performance Summary</h2>
          <div className="performance-grid">
            <div className="performance-card peak">
              <div className="perf-icon">🔥</div>
              <div className="perf-content">
                <p className="perf-label">Peak Engagement</p>
                <p className="perf-value" style={{ color: '#10b981' }}>
                  {(summary.max_score * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            <div className="performance-card lowest">
              <div className="perf-icon">❄️</div>
              <div className="perf-content">
                <p className="perf-label">Lowest Engagement</p>
                <p className="perf-value" style={{ color: '#ef4444' }}>
                  {(summary.min_score * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            <div className="performance-card volatility">
              <div className="perf-icon">📊</div>
              <div className="perf-content">
                <p className="perf-label">Data Volatility</p>
                <p className="perf-value" style={{ color: '#9333ea' }}>
                  {summary.volatility?.toFixed(3)}
                </p>
              </div>
            </div>

            <div className="performance-card stability">
              <div className="perf-icon">✨</div>
              <div className="perf-content">
                <p className="perf-label">Data Stability</p>
                <p className="perf-value" style={{
                  color: summary.volatility <= 0.2 ? '#10b981' : summary.volatility <= 0.5 ? '#f59e0b' : '#ef4444'
                }}>
                  {summary.volatility <= 0.2 ? 'Excellent' : summary.volatility <= 0.5 ? 'Good' : 'Fair'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Info */}
        <div className="report-footer">
          <div className="footer-info">
            <p>Session ID: <code>{sessionId}</code></p>
            <p>
              Session Date:{" "}
              {report.started_at
                ? new Date(report.started_at).toLocaleString()
                : "-"}
            </p>
            {/* <p>
              Report Generated:{" "}
              {report.generated_at
                ? new Date(report.generated_at).toLocaleString()
                : "-"}
            </p> */}
          </div>
          <button onClick={() => navigate('/teacher/sessions')} className="btn btn-secondary">
            View All Sessions
          </button>
        </div>
      </div>
    </div>
  );
}