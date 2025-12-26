import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  TimeScale,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import "chartjs-adapter-date-fns";
import "../styles/global.css";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  TimeScale,
  Tooltip,
  Legend,
  Filler
);

export default function RealTimeEngagement({ 
  sessionId, 
  paused = false, 
  onPointsUpdate = null,
  mode = "live"  // ✅ NEW: "live" or "replay"
}) {
  const POLL_MS = 2000;
  const MAX_POINTS = 300;

  const [points, setPoints] = useState([]);
  const [updateCount, setUpdateCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const lastIsoRef = useRef(null);
  const pollingRef = useRef(null);

  useEffect(() => {
    if (onPointsUpdate) {
      onPointsUpdate(points);
    }
  }, [points, onPointsUpdate]);

  async function fetchUpdates(sinceIso = null) {
    try {
      const token = localStorage.getItem("token");
      if (!token) return [];

      const url = sinceIso
        ? `http://127.0.0.1:8000/api/engagement/sessions/${sessionId}/series/updates?since=${encodeURIComponent(sinceIso)}`
        : `http://127.0.0.1:8000/api/engagement/sessions/${sessionId}/series`;

      const res = await axios.get(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      return res.data || [];
    } catch (err) {
      if (err?.response?.status === 403) {
        console.log("🛑 Session ended - polling stopped");
        return [];
      }
      console.error("❌ fetchUpdates error:", err?.response?.status);
      return [];
    }
  }

  function pushPoints(newPts) {
    if (!Array.isArray(newPts) || newPts.length === 0) return;

    setLoading(false);
    setPoints((prev) => {
      const map = new Map();
      prev.forEach((p) => map.set(p.timestamp, p));
      
      newPts.forEach((p) => {
        if (p.timestamp && (p.score !== undefined && p.score !== null)) {
          map.set(p.timestamp, { timestamp: p.timestamp, score: p.score });
        }
      });

      const merged = Array.from(map.values()).sort(
        (a, b) => new Date(a.timestamp) - new Date(b.timestamp)
      );

      const sliced = merged.slice(-MAX_POINTS);

      if (sliced.length > 0) {
        lastIsoRef.current = sliced[sliced.length - 1].timestamp;
      }

      return sliced;
    });

    setUpdateCount(prev => prev + 1);
  }

 useEffect(() => {
    // ✅ NEW: Don't poll in replay mode
    if (paused || mode === "replay") {
      console.log("⏸️ Polling disabled (paused=" + paused + ", mode=" + mode + ")");
      return;
    }

    let mounted = true;

    async function startPolling() {
      setLoading(true);
      const first = await fetchUpdates(null);
      if (!mounted) return;
      pushPoints(first);

      pollingRef.current = setInterval(async () => {
        if (!mounted) return;
        const updates = await fetchUpdates(lastIsoRef.current);
        if (!mounted) return;
        pushPoints(updates);
      }, POLL_MS);
    }

    startPolling();

    return () => {
      mounted = false;
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [sessionId, paused, mode]);  // ✅ ADD mode to dependencies

  const chartData = {
    datasets: [
      {
        label: "Engagement Score",
        data: points.map((p) => ({
          x: new Date(p.timestamp).getTime(),
          y: p.score,
        })),
        borderColor: "rgb(75, 192, 192)",
        backgroundColor: "rgba(75, 192, 192, 0.1)",
        fill: true,
        tension: 0.25,
        pointRadius: 0,
        borderWidth: 2,
        animation: {
          duration: 300,
        },
      },
    ],
  };

  const chartOptions = {
    animation: { duration: 300 },
    parsing: false,
    normalized: true,
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        type: "time",
        time: { 
          unit: "second", 
          tooltipFormat: "HH:mm:ss",
          displayFormats: { second: "HH:mm:ss" }
        },
        ticks: { autoSkip: true, maxTicksLimit: 10, maxRotation: 0 },
        title: { display: true, text: "Time" }
      },
      y: {
        min: 0,
        max: 1,
        ticks: { stepSize: 0.25 },
        title: { display: true, text: "Engagement" }
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: { 
        mode: "index", 
        intersect: false,
        callbacks: {
          label: (context) => `Score: ${context.parsed.y.toFixed(2)}`,
        }
      },
    },
  };

  return (
    <div className="chart-container">
    <div className="chart-title">
        Real-time Engagement
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {loading && mode === "live" && <span className="spinner"></span>}
          <span className="chart-status">({points.length} points)</span>
          {paused && (
            <span style={{ fontSize: "12px", color: "#f59e0b" }}>⏸️ PAUSED</span>
          )}
          {mode === "replay" && (
            <span style={{ fontSize: "12px", color: "#8b5cf6" }}>📹 REPLAY</span>
          )}
        </div>
      </div>

      {loading && points.length === 0 ? (
        <div className="skeleton skeleton-graph"></div>
      ) : points.length === 0 ? (
        <div className="loading-state">Waiting for engagement data…</div>
      ) : (
        <div style={{ height: 280 }}>
          <Line 
            key={`chart-${updateCount}`} 
            data={chartData} 
            options={chartOptions} 
          />
        </div>
      )}
    </div>
  );
}