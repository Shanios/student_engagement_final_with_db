import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Download, Mail, Share2, Loader, ArrowLeft } from 'lucide-react';

const API = 'http://127.0.0.1:8000';

export default function SessionReportDashboard() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sending, setSending] = useState(false);

  // ✅ Fetch report data on mount
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

  // ✅ Download PDF
  const downloadPDF = async () => {
    try {
      setSending(true);
      const token = localStorage.getItem('token');
      
      const response = await axios.get(
        `${API}/api/engagement/sessions/${sessionId}/report/pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `engagement_report_${sessionId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentElement.removeChild(link);

      alert('✅ PDF downloaded successfully');
    } catch (err) {
      alert('❌ Failed to download PDF');
      console.error(err);
    } finally {
      setSending(false);
    }
  };

  // ✅ Send via Email
  const sendViaEmail = async () => {
    try {
      setSending(true);
      const token = localStorage.getItem('token');
      
      await axios.post(
        `${API}/api/engagement/sessions/${sessionId}/email-report`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );

      alert('✅ Report sent to your email');
      setSending(false);
    } catch (err) {
      alert('❌ Failed to send email');
      console.error(err);
      setSending(false);
    }
  };

  // ✅ Share via WhatsApp
  const shareViaWhatsApp = async () => {
    try {
      setSending(true);
      const token = localStorage.getItem('token');
      
      await axios.post(
        `${API}/api/engagement/sessions/${sessionId}/whatsapp-report`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );

      alert('✅ Report sent to WhatsApp');
      setSending(false);
    } catch (err) {
      alert('❌ Failed to send WhatsApp message');
      console.error(err);
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(to bottom right, #0f172a, #1e293b)',
        padding: '32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{ textAlign: 'center' }}>
          <Loader style={{ width: 48, height: 48, color: '#60a5fa', margin: '0 auto 16px', animation: 'spin 1s linear infinite' }} />
          <p style={{ color: 'white', fontSize: '18px' }}>Loading report...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(to bottom right, #0f172a, #1e293b)',
        padding: '32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{
          background: '#7c2d12',
          borderLeft: '4px solid #dc2626',
          padding: '24px',
          borderRadius: '8px',
          color: 'white',
          maxWidth: '500px'
        }}>
          <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '8px' }}>❌ Error Loading Report</h2>
          <p>{error}</p>
          <button
            onClick={fetchReport}
            style={{
              marginTop: '16px',
              background: '#991b1b',
              color: 'white',
              padding: '8px 16px',
              borderRadius: '4px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(to bottom right, #0f172a, #1e293b)',
        padding: '32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{
          background: '#78350f',
          borderLeft: '4px solid #f59e0b',
          padding: '24px',
          borderRadius: '8px',
          color: 'white',
          maxWidth: '500px'
        }}>
          <p style={{ fontSize: '18px' }}>⏳ Report is being generated...</p>
          <p style={{ fontSize: '13px', color: '#d1d5db', marginTop: '8px' }}>Please check back in a few moments</p>
          <button
            onClick={fetchReport}
            style={{
              marginTop: '16px',
              background: '#b45309',
              color: 'white',
              padding: '8px 16px',
              borderRadius: '4px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            Refresh
          </button>
        </div>
      </div>
    );
  }

  const summary = report.analytics?.summary || {};
  const distribution = report.analytics?.distribution || {};
  const critical = report.analytics?.critical_moments || {};

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(to bottom right, #0f172a, #1e293b)',
      padding: '32px'
    }}>
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>

      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ marginBottom: '32px' }}>
          <button
            onClick={() => navigate('/teacher/sessions')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'transparent',
              color: '#60a5fa',
              border: 'none',
              cursor: 'pointer',
              fontSize: '14px',
              marginBottom: '16px',
              padding: '0'
            }}
          >
            <ArrowLeft size={16} />
            Back to Sessions
          </button>
          
          <h1 style={{ fontSize: '32px', fontWeight: 'bold', color: 'white', marginBottom: '8px' }}>
            📊 {report.title || 'Session Analytics'}
          </h1>
          <p style={{ color: '#9ca3af' }}>
            Session ID: {sessionId} | Generated: {new Date(report.generated_at).toLocaleString()}
          </p>
        </div>

        {/* Action Buttons */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginBottom: '32px'
        }}>
          <button
            onClick={downloadPDF}
            disabled={sending}
            style={{
              background: '#2563eb',
              color: 'white',
              fontWeight: 'bold',
              padding: '12px 24px',
              borderRadius: '8px',
              border: 'none',
              cursor: sending ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              opacity: sending ? 0.6 : 1,
              fontSize: '16px'
            }}
          >
            <Download size={20} />
            {sending ? 'Downloading...' : 'Download PDF'}
          </button>

          <button
            onClick={sendViaEmail}
            disabled={sending}
            style={{
              background: '#16a34a',
              color: 'white',
              fontWeight: 'bold',
              padding: '12px 24px',
              borderRadius: '8px',
              border: 'none',
              cursor: sending ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              opacity: sending ? 0.6 : 1,
              fontSize: '16px'
            }}
          >
            <Mail size={20} />
            {sending ? 'Sending...' : 'Send Email'}
          </button>

          <button
            onClick={shareViaWhatsApp}
            disabled={sending}
            style={{
              background: '#9333ea',
              color: 'white',
              fontWeight: 'bold',
              padding: '12px 24px',
              borderRadius: '8px',
              border: 'none',
              cursor: sending ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              opacity: sending ? 0.6 : 1,
              fontSize: '16px'
            }}
          >
            <Share2 size={20} />
            {sending ? 'Sending...' : 'Share WhatsApp'}
          </button>
        </div>

        {/* Key Metrics */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '24px',
          marginBottom: '32px'
        }}>
          <div style={{
            background: '#1e3a8a',
            borderLeft: '4px solid #60a5fa',
            borderRadius: '8px',
            padding: '24px'
          }}>
            <p style={{ color: '#d1d5db', fontSize: '13px' }}>Avg Engagement</p>
            <p style={{ fontSize: '32px', fontWeight: 'bold', color: 'white', marginTop: '8px' }}>
              {(summary.avg_score * 100).toFixed(1)}%
            </p>
          </div>

          <div style={{
            background: '#064e3b',
            borderLeft: '4px solid #10b981',
            borderRadius: '8px',
            padding: '24px'
          }}>
            <p style={{ color: '#d1d5db', fontSize: '13px' }}>Attention Score</p>
            <p style={{ fontSize: '32px', fontWeight: 'bold', color: 'white', marginTop: '8px' }}>
              {summary.attention_score}/100
            </p>
          </div>

          <div style={{
            background: '#581c87',
            borderLeft: '4px solid #d946ef',
            borderRadius: '8px',
            padding: '24px'
          }}>
            <p style={{ color: '#d1d5db', fontSize: '13px' }}>Focus Time</p>
            <p style={{ fontSize: '32px', fontWeight: 'bold', color: 'white', marginTop: '8px' }}>
              {summary.focus_time_percentage?.toFixed(1)}%
            </p>
          </div>

          <div style={{
            background: '#7c2d12',
            borderLeft: '4px solid #f97316',
            borderRadius: '8px',
            padding: '24px'
          }}>
            <p style={{ color: '#d1d5db', fontSize: '13px' }}>Duration</p>
            <p style={{ fontSize: '32px', fontWeight: 'bold', color: 'white', marginTop: '8px' }}>
              {summary.duration_formatted}
            </p>
          </div>
        </div>

        {/* Graphs */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
          gap: '32px',
          marginBottom: '32px'
        }}>
          {report.graphs?.engagement_timeline && (
            <div style={{
              background: '#1f2937',
              borderRadius: '8px',
              padding: '24px'
            }}>
              <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: 'white', marginBottom: '16px' }}>
                Engagement Timeline
              </h3>
              <img
                src={`data:image/png;base64,${report.graphs.engagement_timeline}`}
                alt="Engagement Timeline"
                style={{ width: '100%', borderRadius: '4px' }}
              />
            </div>
          )}

          {report.graphs?.distribution_chart && (
            <div style={{
              background: '#1f2937',
              borderRadius: '8px',
              padding: '24px'
            }}>
              <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: 'white', marginBottom: '16px' }}>
                Engagement Distribution
              </h3>
              <img
                src={`data:image/png;base64,${report.graphs.distribution_chart}`}
                alt="Distribution Chart"
                style={{ width: '100%', borderRadius: '4px' }}
              />
            </div>
          )}
        </div>

        {/* Detailed Metrics */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '32px',
          marginBottom: '32px'
        }}>
          {/* Engagement Breakdown */}
          <div style={{
            background: '#1f2937',
            borderRadius: '8px',
            padding: '24px'
          }}>
            <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: 'white', marginBottom: '16px' }}>
              Engagement Breakdown
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ color: '#d1d5db' }}>High (&gt;67%)</span>
                  <span style={{ color: '#10b981', fontWeight: 'bold' }}>
                    {(distribution.high_engagement * 100).toFixed(1)}%
                  </span>
                </div>
                <div style={{ background: '#374151', borderRadius: '8px', height: '8px', overflow: 'hidden' }}>
                  <div
                    style={{
                      background: '#10b981',
                      height: '100%',
                      width: `${distribution.high_engagement * 100}%`,
                      transition: 'width 0.3s'
                    }}
                  />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ color: '#d1d5db' }}>Medium (33-67%)</span>
                  <span style={{ color: '#eab308', fontWeight: 'bold' }}>
                    {(distribution.medium_engagement * 100).toFixed(1)}%
                  </span>
                </div>
                <div style={{ background: '#374151', borderRadius: '8px', height: '8px', overflow: 'hidden' }}>
                  <div
                    style={{
                      background: '#eab308',
                      height: '100%',
                      width: `${distribution.medium_engagement * 100}%`,
                      transition: 'width 0.3s'
                    }}
                  />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ color: '#d1d5db' }}>Low (&lt;33%)</span>
                  <span style={{ color: '#ef4444', fontWeight: 'bold' }}>
                    {(distribution.low_engagement * 100).toFixed(1)}%
                  </span>
                </div>
                <div style={{ background: '#374151', borderRadius: '8px', height: '8px', overflow: 'hidden' }}>
                  <div
                    style={{
                      background: '#ef4444',
                      height: '100%',
                      width: `${distribution.low_engagement * 100}%`,
                      transition: 'width 0.3s'
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Critical Moments */}
          <div style={{
            background: '#1f2937',
            borderRadius: '8px',
            padding: '24px'
          }}>
            <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: 'white', marginBottom: '16px' }}>
              ⚠️ Critical Moments
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '12px',
                background: '#374151',
                borderRadius: '6px'
              }}>
                <span style={{ color: '#d1d5db' }}>Distraction Spikes</span>
                <span style={{ color: '#ef4444', fontWeight: 'bold', fontSize: '18px' }}>
                  {critical.total_spikes || 0}
                </span>
              </div>

              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '12px',
                background: '#374151',
                borderRadius: '6px'
              }}>
                <span style={{ color: '#d1d5db' }}>Engagement Dropoffs</span>
                <span style={{ color: '#f59e0b', fontWeight: 'bold', fontSize: '18px' }}>
                  {critical.total_dropoffs || 0}
                </span>
              </div>

              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '12px',
                background: '#374151',
                borderRadius: '6px'
              }}>
                <span style={{ color: '#d1d5db' }}>Peak Periods</span>
                <span style={{ color: '#10b981', fontWeight: 'bold', fontSize: '18px' }}>
                  {critical.total_peaks || 0}
                </span>
              </div>

              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '12px',
                background: '#374151',
                borderRadius: '6px'
              }}>
                <span style={{ color: '#d1d5db' }}>Total Data Points</span>
                <span style={{ color: '#60a5fa', fontWeight: 'bold', fontSize: '18px' }}>
                  {summary.total_points || 0}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Performance Summary */}
        <div style={{
          background: '#1f2937',
          borderRadius: '8px',
          padding: '24px'
        }}>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: 'white', marginBottom: '16px' }}>
            📈 Performance Summary
          </h3>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '16px',
            textAlign: 'center'
          }}>
            <div>
              <p style={{ color: '#9ca3af', fontSize: '13px' }}>Peak Engagement</p>
              <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#10b981', marginTop: '8px' }}>
                {(summary.max_score * 100).toFixed(1)}%
              </p>
            </div>

            <div>
              <p style={{ color: '#9ca3af', fontSize: '13px' }}>Lowest Engagement</p>
              <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#ef4444', marginTop: '8px' }}>
                {(summary.min_score * 100).toFixed(1)}%
              </p>
            </div>

            <div>
              <p style={{ color: '#9ca3af', fontSize: '13px' }}>Volatility</p>
              <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#9333ea', marginTop: '8px' }}>
                {summary.volatility?.toFixed(3)}
              </p>
            </div>

            <div>
              <p style={{ color: '#9ca3af', fontSize: '13px' }}>Data Stability</p>
              <p style={{
                fontSize: '24px',
                fontWeight: 'bold',
                color: summary.volatility <= 0.2 ? '#10b981' : summary.volatility <= 0.5 ? '#f59e0b' : '#ef4444',
                marginTop: '8px'
              }}>
                {summary.volatility <= 0.2 ? '✅ High' : summary.volatility <= 0.5 ? '⚠️ Med' : '❌ Low'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}