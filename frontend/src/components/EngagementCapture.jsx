// src/components/EngagementCapture.jsx
import React, { useEffect, useRef, useState } from "react";
import * as tf from "@tensorflow/tfjs-core";
import "@tensorflow/tfjs-backend-webgl";
import * as faceLandmarksDetection from "@tensorflow-models/face-landmarks-detection";
import axios from "axios";

/*
  What this component does:
  - Accesses webcam
  - Loads TF face-landmarks detection (MediaPipe FaceMesh)
  - Samples at `sampleFps` and computes approximate features:
      head_pitch, head_yaw, eye_open_left, eye_open_right, blink_rate, gaze_attention
  - Buffers features and POSTs to /api/engagement/predict_batch every `batchIntervalMs`
  - Sends Authorization: Bearer <token> if present in localStorage key "token"
*/

export default function EngagementCapture({
  userId = null,           // optional: send user id to backend
  sampleFps = 2,          // frames/second to sample
  batchIntervalMs = 5000, // how often to send batched features
  batchSize = 10,         // fallback batch flush size
  enabled = true,         // set false to stop capturing
}) {
  const videoRef = useRef(null);
  const modelRef = useRef(null);
  const rafRef = useRef(null);
  const [running, setRunning] = useState(false);
  const bufferRef = useRef([]);
  const blinkStateRef = useRef({
    leftOpen: true,
    rightOpen: true,
    leftLastChange: null,
    rightLastChange: null,
    leftBlinks: 0,
    rightBlinks: 0,
    windowStart: Date.now(),
  });

  // Helpers -----------------------------------------------------

  function eyeAspectRatio(upper, lower) {
    // upper and lower are arrays of two points: [p1, p2] measured vertically
    // cheap EAR approximation using vertical / horizontal distances
    // Here we expect single vertical distance from eyelid landmarks
    // To simplify, we will accept a numeric vertical openness value passed in instead.
    return upper - lower;
  }

  function vec(a, b) {
    return [b[0] - a[0], b[1] - a[1], (b[2] || 0) - (a[2] || 0)];
  }
  function dot(u, v) {
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2];
  }
  function norm(u) {
    return Math.sqrt(dot(u, u)) || 1e-6;
  }
  function angleBetween(u, v) {
    const cos = dot(u, v) / (norm(u) * norm(v));
    return Math.acos(Math.max(-1, Math.min(1, cos)));
  }

  function estimateHeadAngles(keypoints) {
    // keypoints: array of landmarks in [x,y,z] (normalized to video pixels)
    // Using simple heuristic: use eye centers and nose tip to compute yaw and pitch
    // Indices follow MediaPipe's face mesh key indexing (approx):
    // - left eye center ~ 468..473 (iris); right eye center ~ 473..478
    // - nose tip ~ 1 or 4 depending on model; use 1 (near tip)
    // We'll find approximate centers by averaging eye landmarks groups if available.

    // Fallback indexes: use landmarks by position: left eye (33..133 region), right eye (263..362)
    // We'll take these canonical indices for mediapipe facemesh:
    const LEFT_EYE_IDX = [33, 133, 160, 158, 153]; // outer landmarks
    const RIGHT_EYE_IDX = [362, 263, 387, 385, 380];
    const NOSE_TIP_IDX = 1;

    const pickAvg = (idxs) => {
      let sum = [0, 0, 0];
      let c = 0;
      for (let i of idxs) {
        if (!keypoints[i]) continue;
        sum[0] += keypoints[i].x;
        sum[1] += keypoints[i].y;
        sum[2] += keypoints[i].z || 0;
        c++;
      }
      if (c === 0) return null;
      return [sum[0] / c, sum[1] / c, sum[2] / c];
    };

    const leftEye = pickAvg(LEFT_EYE_IDX);
    const rightEye = pickAvg(RIGHT_EYE_IDX);
    const nose = keypoints[NOSE_TIP_IDX]
      ? [keypoints[NOSE_TIP_IDX].x, keypoints[NOSE_TIP_IDX].y, keypoints[NOSE_TIP_IDX].z || 0]
      : null;

    if (!leftEye || !rightEye || !nose) return { pitch: 0, yaw: 0 };

    // vector across eyes
    const eyeVec = vec(leftEye, rightEye); // left→right
    // vector nose→mid-eye
    const midEye = [(leftEye[0] + rightEye[0]) / 2, (leftEye[1] + rightEye[1]) / 2, (leftEye[2] + rightEye[2]) / 2];
    const noseVec = vec(nose, midEye);

    // Yaw ~ horizontal rotation (rotate left-right) -> sign of eyeVec.x vs nose displacement
    // Use angle between eyeVec and horizontal axis to estimate yaw roughly
    const horiz = [1, 0, 0];
    const yawRad = angleBetween(eyeVec, horiz);
    // if nose is shifted left (in image coords), determine sign
    const yawSign = (nose[0] - midEye[0]) < 0 ? -1 : 1;
    const yaw = yawSign * yawRad; // radians

    // Pitch ~ up/down tilt. Use vertical component of noseVec vs forward assume
    // If nose is lower than midEye (smaller y), head pitched down (positive pitch)
    const pitch = Math.atan2(noseVec[1], noseVec[2] || 1e-6); // rough

    return { pitch: pitch, yaw: yaw };
  }

  function computeEyeOpeness(landmarks, side = "left") {
    // Very rough: use vertical distance between eyelid landmarks normalized by eye width.
    // MediaPipe indices for eyelids approximate:
    // left: upper 159, lower 145, left corner 33, right corner 133
    const LEFT_UP = 159,
      LEFT_LO = 145,
      LEFT_L = 33,
      LEFT_R = 133;
    const RIGHT_UP = 386,
      RIGHT_LO = 374,
      RIGHT_L = 362,
      RIGHT_R = 263;

    const idxs = side === "left" ? { u: LEFT_UP, l: LEFT_LO, L: LEFT_L, R: LEFT_R } : { u: RIGHT_UP, l: RIGHT_LO, L: RIGHT_L, R: RIGHT_R };

    if (!landmarks[idxs.u] || !landmarks[idxs.l] || !landmarks[idxs.L] || !landmarks[idxs.R]) {
      return 0.9; // assume open
    }
    const up = [landmarks[idxs.u].x, landmarks[idxs.u].y];
    const lo = [landmarks[idxs.l].x, landmarks[idxs.l].y];
    const left = [landmarks[idxs.L].x, landmarks[idxs.L].y];
    const right = [landmarks[idxs.R].x, landmarks[idxs.R].y];

    const vert = Math.hypot(up[0] - lo[0], up[1] - lo[1]);
    const hor = Math.hypot(left[0] - right[0], left[1] - right[1]) || 1e-6;
    const ratio = vert / hor;
    // normalized: typical open eye ratios ~ 0.2-0.35; closed ~ 0.02-0.08
    // scale into 0..1
    const scaled = (ratio - 0.02) / (0.35 - 0.02);
    return Math.max(0, Math.min(1, scaled));
  }

  // Blink tracking windowed per-minute
  function updateBlinkCounters(leftOpen, rightOpen) {
    const s = blinkStateRef.current;
    const now = Date.now();

    // left
    if (leftOpen !== s.leftOpen) {
      // state changed
      if (!leftOpen && s.leftOpen) {
        // became closed -> mark time
        s.leftLastChange = now;
      } else if (leftOpen && !s.leftOpen) {
        // opened from closed = a blink
        s.leftBlinks += 1;
        s.leftLastChange = now;
      }
      s.leftOpen = leftOpen;
    }

    // right
    if (rightOpen !== s.rightOpen) {
      if (!rightOpen && s.rightOpen) {
        s.rightLastChange = now;
      } else if (rightOpen && !s.rightOpen) {
        s.rightBlinks += 1;
        s.rightLastChange = now;
      }
      s.rightOpen = rightOpen;
    }

    // window reset every 60s
    if (now - s.windowStart > 60000) {
      s.leftBlinks = 0;
      s.rightBlinks = 0;
      s.windowStart = now;
    }
  }

  // Compute gaze_attention: approximate by how close iris is to center of eye box (0..1)
  function computeGazeAttention(landmarks) {
    // approximate by distance between nose tip and mid of eyes horizontally normalized
    const leftEye = [landmarks[33].x, landmarks[33].y];
    const rightEye = [landmarks[263].x, landmarks[263].y];
    const midEye = [(leftEye[0] + rightEye[0]) / 2, (leftEye[1] + rightEye[1]) / 2];
    const nose = [landmarks[1].x, landmarks[1].y];
    const dx = Math.abs(nose[0] - midEye[0]);
    // larger dx => looking away. Normalize by eye distance
    const eyeDist = Math.hypot(leftEye[0] - rightEye[0], leftEye[1] - rightEye[1]) || 1e-6;
    const normDev = Math.min(1, dx / eyeDist);
    // attention score = 1 - normalized deviation
    return Math.max(0, 1 - normDev);
  }

  // Frame processing ------------------------------------------------

  useEffect(() => {
    if (!enabled) return;
    let mounted = true;
    let model;
    let video = videoRef.current;
    let intervalId;

    async function initCamera() {
      video = videoRef.current;
      if (!video) return;
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
        video.srcObject = stream;
        await video.play();
        return true;
      } catch (err) {
        console.error("camera init failed", err);
        return false;
      }
    }

    async function loadModel() {
      await tf.setBackend("webgl");
      model = await faceLandmarksDetection.load(faceLandmarksDetection.SupportedPackages.mediapipeFacemesh, {
        maxFaces: 1,
        refineLandmarks: true,
      });
      modelRef.current = model;
    }

    async function start() {
      const ok = await initCamera();
      if (!ok) return;
      await loadModel();
      setRunning(true);

      const sampleMs = Math.max(200, Math.round(1000 / sampleFps)); // limit >=200ms for perf
      intervalId = setInterval(async () => {
        if (!mounted) return;
        if (!video || video.readyState < 2) return;
        try {
          // detect
          const predictions = await modelRef.current.estimateFaces({ input: video, flipHorizontal: false });
          if (!predictions || predictions.length === 0) {
            return;
          }
          const p = predictions[0];
          const landmarks = p.scaledMesh || p.keypoints3D || p.keypoints || [];
          // NOTE: landmarks format depends on package; scaledMesh has objects or arrays; adapt:
          // In mediapipe facemesh, scaledMesh is array of [x,y,z] (numbers)
          // convert to uniform {x,y,z}
          let keys = [];
          if (Array.isArray(landmarks) && landmarks.length && Array.isArray(landmarks[0])) {
            keys = landmarks.map((a) => ({ x: a[0], y: a[1], z: a[2] ?? 0 }));
          } else if (Array.isArray(landmarks) && landmarks.length && landmarks[0].x !== undefined) {
            keys = landmarks;
          } else if (p.keypoints && p.keypoints.length) {
            keys = p.keypoints.map(k => ({ x: k.x, y: k.y, z: k.z ?? 0 }));
          } else {
            // fallback: skip
            return;
          }

          // compute features
          const { pitch, yaw } = estimateHeadAngles(keys);
          const eyeLeft = computeEyeOpeness(keys, "left");
          const eyeRight = computeEyeOpeness(keys, "right");

          // blink detection: treat eye open < 0.15 as closed
          const leftClosed = eyeLeft < 0.15;
          const rightClosed = eyeRight < 0.15;
          updateBlinkCounters(!leftClosed, !rightClosed); // pass leftOpen/rightOpen booleans

          const s = blinkStateRef.current;
          // blink_rate in blinks per minute (approx)
          const blinkRate = (s.leftBlinks + s.rightBlinks) / 2; // approx per minute window

          const gaze = computeGazeAttention(keys);

          const feat = {
            timestamp: new Date().toISOString(),
            user_id: userId,
            head_pitch: pitch,                    // radians (can convert to deg if model expects that)
            head_yaw: yaw,
            eye_open_left: eyeLeft,
            eye_open_right: eyeRight,
            blink_rate: blinkRate,
            gaze_attention: gaze,
            extra: { raw_landmarks_count: keys.length },
          };

          // Buffer
          bufferRef.current.push(feat);
          // Flush by size
          if (bufferRef.current.length >= batchSize) {
            await flushBuffer();
          }
        } catch (err) {
          console.error("frame processing err", err);
        }
      }, sampleMs);

      // periodic flush
      const periodic = setInterval(() => {
        flushBuffer().catch((e) => console.error("flush err", e));
      }, batchIntervalMs);

      // store cleanup
      rafRef.current = { intervalId, periodic };
    }

    async function flushBuffer() {
      if (!bufferRef.current.length) return;
      const payload = {
        user_id: userId,
        items: bufferRef.current.splice(0, bufferRef.current.length),
      };
      try {
        const token = localStorage.getItem("token");
        await axios.post("/api/engagement/predict_batch", payload, {
          baseURL: "http://127.0.0.1:8000",
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        });
      } catch (err) {
        console.error("send batch err", err);
        // on failure, re-insert items at head (simple retry)
        bufferRef.current.unshift(...payload.items);
        // cap buffer size
        if (bufferRef.current.length > 500) bufferRef.current = bufferRef.current.slice(-500);
      }
    }

    start();

    return () => {
      mounted = false;
      setRunning(false);
      // stop camera
      const v = videoRef.current;
      if (v && v.srcObject) {
        v.srcObject.getTracks().forEach((t) => t.stop());
        v.srcObject = null;
      }
      // clear intervals
      if (rafRef.current) {
        clearInterval(rafRef.current.intervalId);
        clearInterval(rafRef.current.periodic);
      }
      // flush one last time (fire and forget)
      flushBuffer().catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, sampleFps, batchIntervalMs, batchSize, userId]);

  return (
    <div style={{ position: "relative" }}>
      <video
        ref={videoRef}
        style={{ width: 320, height: 240, borderRadius: 8, transform: "scaleX(-1)" }}
        playsInline
        muted
      />
      <div style={{ marginTop: 8 }}>
        <small>Engagement capture: {running ? "running" : "initializing/paused"}</small>
      </div>
    </div>
  );
}
