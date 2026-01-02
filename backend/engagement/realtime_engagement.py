# ========== ENCODING FIX ==========
import sys
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
# ====================================

import cv2
import mediapipe as mp
import numpy as np
import math
from collections import deque
import joblib
import os
import csv
import datetime
import signal
import requests
import threading
import time
import argparse
from dotenv import load_dotenv 
load_dotenv()

# ========== FILE LOGGING ==========
debug_log_file = None

def init_debug_log():
    """Initialize debug log file"""
    global debug_log_file
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_debug.log")
    debug_log_file = open(log_path, "w", encoding='utf-8')
    print_log(f"🟢 Debug log started at {datetime.datetime.utcnow().isoformat()}")

def print_log(msg):
    """Print to both console and file"""
    print(msg)
    if debug_log_file:
        debug_log_file.write(msg + "\n")
        debug_log_file.flush()

def close_debug_log():
    """Close debug log file"""
    if debug_log_file:
        debug_log_file.close()
# ===================================

# ✅ GLOBAL SESSION STATE
SESSION_ACTIVE = True

# =========================================================
# COMMAND LINE ARGUMENTS
# =========================================================
parser = argparse.ArgumentParser(description="Real-time engagement ML model")
parser.add_argument("--session-id", type=int, required=True, help="Engagement session ID")
parser.add_argument("--student-id", type=int, required=False, help="Student ID (optional)")
parser.add_argument("--backend", type=str, default="http://127.0.0.1:8000", help="Backend URL")
parser.add_argument("--token", type=str, required=False, help="JWT authentication token")
args = parser.parse_args()

SESSION_ID = args.session_id
STUDENT_ID = args.student_id
BACKEND_BASE = args.backend

print(f"\n✅ ML Script Started")
print(f"   Session ID: {SESSION_ID}")
if STUDENT_ID:
    print(f"   Student ID: {STUDENT_ID}")
print(f"   Backend: {BACKEND_BASE}\n")

# =========================================================
# PATH RESOLUTION (MODEL)
# =========================================================
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(THIS_DIR)
MODEL_CANDIDATES = [
    os.path.join(THIS_DIR, "engagement_model.pkl"),
    os.path.join(PARENT_DIR, "engagement_model.pkl"),
    os.path.join(PARENT_DIR, "engagement", "engagement_model.pkl"),
]
MODEL_PATH = None
for p in MODEL_CANDIDATES:
    if os.path.exists(p):
        MODEL_PATH = p
        break
if MODEL_PATH is None:
    print("❌ engagement_model.pkl not found")
    sys.exit(1)
print(f"✅ Model found at: {MODEL_PATH}\n")

# =========================================================
# DEVICE AUTH
# =========================================================
DEVICE_KEY = os.getenv("CAMERA_DEVICE_KEY")
if not DEVICE_KEY:
    print("❌ CAMERA_DEVICE_KEY environment variable NOT SET")
    sys.exit(1)
print("✅ Device key loaded\n")

# =========================================================
# CONFIG
# =========================================================
WINDOW_SIZE = 10
EAR_THRESHOLD = 0.18
POST_TIMEOUT = 5.0
BACKEND_UPLOAD = True
UPLOAD_INTERVAL = 1.0  # Upload every 1 second
LOG_PATH = os.path.join(THIS_DIR, "engagement_log.csv")

# =========================================================
# MEDIAPIPE SETUP
# =========================================================
mp_face_mesh = mp.solutions.face_mesh
LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [263, 387, 385, 362, 380, 373]

# =========================================================
# OFFLINE BUFFER CLASS
# =========================================================
class OfflineBuffer:
    def __init__(self, max_size=100, stale_threshold_hours=1):
        self.queue = deque(maxlen=max_size)
        self.stale_threshold = stale_threshold_hours * 3600
        self.max_retries = 5
    
    def add(self, session_id, score, ear, timestamp_iso):
        point = {
            "session_id": session_id,
            "score": score,
            "ear": ear,
            "timestamp": timestamp_iso,
            "added_at": time.time(),
            "retry_count": 0,
        }
        self.queue.append(point)
        print_log(f"📦 Point buffered (queue size: {len(self.queue)})")
    
    def is_stale(self, point):
        age = time.time() - point["added_at"]
        return age > self.stale_threshold
    
    def get_next_retry(self):
        if not self.queue:
            return None
        
        point = self.queue[0]
        
        if self.is_stale(point):
            self.queue.popleft()
            print_log(f"⏰ Dropped stale point")
            return self.get_next_retry()
        
        backoff_delay = 2 ** point["retry_count"]
        time_since_added = time.time() - point["added_at"]
        
        if time_since_added < backoff_delay:
            return None
        
        if point["retry_count"] >= self.max_retries:
            self.queue.popleft()
            print_log(f"❌ Dropped point after {self.max_retries} retries")
            return self.get_next_retry()
        
        return point
    
    def retry(self, success):
        if not self.queue:
            return
        
        point = self.queue[0]
        if success:
            self.queue.popleft()
            print_log(f"✅ Point uploaded from buffer")
        else:
            point["retry_count"] += 1
            print_log(f"🔄 Retry #{point['retry_count']}")
    
    def size(self):
        return len(self.queue)

# =========================================================
# UTILS
# =========================================================
def euclidean_dist(p1, p2):
    return math.dist(p1, p2)

def eye_aspect_ratio(eye_pts):
    p1, p2, p3, p4, p5, p6 = eye_pts
    return (euclidean_dist(p2, p6) + euclidean_dist(p3, p5)) / (2.0 * euclidean_dist(p1, p4))

def get_eye_points(landmarks, indices, w, h):
    return [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in indices]

def extract_features_from_window(ear_window):
    arr = np.array(ear_window)
    return [
        float(np.mean(arr)),
        float(np.std(arr)),
        float(np.min(arr)),
        float(np.max(arr)),
        float(np.mean(arr < EAR_THRESHOLD)),
    ]

def graceful_exit(cap, logf):
    try:
        cap.release()
        cv2.destroyAllWindows()
        logf.close()
    finally:
        sys.exit(0)

# =========================================================
# BACKEND UPLOAD
# =========================================================
buffer = OfflineBuffer(max_size=100, stale_threshold_hours=1)

def upload_point(session_id, score, ear, timestamp_iso, retry_from_buffer=False):
    """Upload engagement score to backend"""
    global SESSION_ACTIVE
    
    url = f"{BACKEND_BASE}/api/engagement/sessions/{session_id}/points"
    
    payload = {
        "score": float(score),
        "ear": float(ear) if ear is not None else None,
        "timestamp": timestamp_iso,
    }

    headers = {
        "Content-Type": "application/json",
        "X-DEVICE-KEY": DEVICE_KEY,
    }
        
    try:
        ear_str = f"{ear:.3f}" if ear is not None else "N/A"
        print_log(f"📤 POST {url} | Score: {score:.3f}, EAR: {ear_str}")

        r = requests.post(url, json=payload, headers=headers, timeout=POST_TIMEOUT)
        
        if r.status_code in (200, 201):
            print_log(f"✅ Upload success ({r.status_code})")
            if retry_from_buffer:
                buffer.retry(success=True)
            return True

        elif r.status_code == 403:
            SESSION_ACTIVE = False
            print_log("🛑 Session ended (403). Stopping uploads and clearing buffer.")
            buffer.queue.clear()
            return False
        
        elif r.status_code == 429:
            print_log("⏳ Rate limited (429). Buffering point.")
            if not retry_from_buffer:
                buffer.add(session_id, score, ear, timestamp_iso)
            else:
                buffer.retry(success=False)
            return False

        else:
            print_log(f"❌ Upload failed: Status {r.status_code}")
            if not retry_from_buffer:
                buffer.add(session_id, score, ear, timestamp_iso)
            else:
                buffer.retry(success=False)
            return False
    
    except requests.exceptions.Timeout:
        print_log(f"⏱️  Upload timeout - buffering")
        if not retry_from_buffer:
            buffer.add(session_id, score, ear, timestamp_iso)
        else:
            buffer.retry(success=False)
        return False
    
    except requests.exceptions.ConnectionError as e:
        print_log(f"🔌 Connection error: {BACKEND_BASE}")
        if not retry_from_buffer:
            buffer.add(session_id, score, ear, timestamp_iso)
        else:
            buffer.retry(success=False)
        return False
    
    except Exception as e:
        print_log(f"❌ Upload error: {e}")
        if not retry_from_buffer:
            buffer.add(session_id, score, ear, timestamp_iso)
        else:
            buffer.retry(success=False)
        return False

def upload_point_background(session_id, score, ear, ts):
    """Upload in background thread"""
    threading.Thread(
        target=upload_point,
        args=(session_id, score, ear, ts, False),
        daemon=True
    ).start()

def retry_buffered_points():
    """Periodically retry buffered points"""
    while True:
        time.sleep(2)
        point = buffer.get_next_retry()
        if point:
            print_log(f"🔄 Retrying buffered point")
            upload_point(
                point["session_id"],
                point["score"],
                point["ear"],
                point["timestamp"],
                retry_from_buffer=True
            )

# =========================================================
# MAIN
# =========================================================
def main():
    init_debug_log()
    print_log("🟢 [1] main() started")

    try:
        model = joblib.load(MODEL_PATH)
        print_log("🟢 [2] model loaded")
    except Exception as e:
        print_log(f"❌ [2] Model load failed: {e}")
        close_debug_log()
        sys.exit(1)

    last_upload_time = time.time() - UPLOAD_INTERVAL
    last_uploaded_prob = None  # ✅ INITIALIZE THIS

    try:
        retry_thread = threading.Thread(target=retry_buffered_points, daemon=True)
        retry_thread.start()
        print_log("🟢 [3] retry thread started")
    except Exception as e:
        print_log(f"❌ [3] Retry thread failed: {e}")
        close_debug_log()
        sys.exit(1)

    try:
        new_file = not os.path.exists(LOG_PATH)
        logf = open(LOG_PATH, "a", newline="")
        writer = csv.writer(logf)
        if new_file:
            writer.writerow(["ts", "pred", "prob", "mean", "std", "min", "max", "below_thresh"])
        print_log("🟢 [4] CSV log opened")
    except Exception as e:
        print_log(f"❌ [4] Log file failed: {e}")
        close_debug_log()
        sys.exit(1)

    try:
        cap = None
        # ✅ Try virtual camera first (OBS), then real camera
        for camera_id in [1, 0]:
            print_log(f"🎥 Trying camera {camera_id}...")
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                ok, test_frame = cap.read()
                if ok:
                    print_log(f"✅ Successfully using camera {camera_id}")
                    break
                else:
                    print_log(f"⚠️  Camera {camera_id} open but can't read")
                    cap.release()
            else:
                print_log(f"❌ Camera {camera_id} not available")
        
        # Check if we got a working camera
        if cap is None or not cap.isOpened():
            print_log("❌ [5] No camera available")
            close_debug_log()
            sys.exit(1)
        
        print_log("🟢 [5] Camera opened successfully")
        
    except Exception as e:
        print_log(f"❌ [5] Camera error: {e}")
        close_debug_log()
        sys.exit(1)

    ear_window = deque(maxlen=WINDOW_SIZE)
    current_prob = 0.0
    current_status = "Collecting"
    last_valid_prob = 0.0
    signal.signal(signal.SIGINT, lambda s, f: graceful_exit(cap, logf))
    signal.signal(signal.SIGTERM, lambda s, f: graceful_exit(cap, logf))
    print_log("🟢 [6] Signal handlers registered")

    try:
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.2,
            min_tracking_confidence=0.2,
        )
        print_log("🟢 [7] Face mesh initialized")
    except Exception as e:
        print_log(f"❌ [7] Face mesh failed: {e}")
        cap.release()
        close_debug_log()
        sys.exit(1)

    print_log("🟢 [8] Starting frame loop")

    with face_mesh:
        frame_count = 0
        upload_count = 0
        face_detected_count = 0

        while True:
            # ✅ Check if session is still active
            if not SESSION_ACTIVE:
                print_log("🛑 Session no longer active. Stopping ML process.")
                break

            try:
                ok, frame = cap.read()
                if not ok:
                    print_log(f"❌ [9] Camera read failed after {frame_count} frames")
                    break

                frame_count += 1

                if frame_count % 100 == 0:
                    print_log(f"🟢 Progress: {frame_count} frames, {upload_count} uploads, {face_detected_count} faces")

                frame = cv2.flip(frame, 1)
                h, w, _ = frame.shape
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb)

                ts = datetime.datetime.utcnow().isoformat()
                ear_avg = None

                # ✅ Process inference regardless of face detection
                if results.multi_face_landmarks:
                    face_detected_count += 1
                    lm = results.multi_face_landmarks[0].landmark
                    ear_values = []

                    # Left eye
                    try:
                        left_eye = get_eye_points(lm, LEFT_EYE_IDX, w, h)
                        ear_values.append(eye_aspect_ratio(left_eye))
                    except:
                        pass

                    # Right eye
                    try:
                        right_eye = get_eye_points(lm, RIGHT_EYE_IDX, w, h)
                        ear_values.append(eye_aspect_ratio(right_eye))
                    except:
                        pass

                    if ear_values:
                        ear_avg = float(np.mean(ear_values))
                        ear_window.append(ear_avg)
                    else:
                        ear_avg = None

                    # ✅ Do inference when we have enough EAR samples
                    if len(ear_window) >= 3:
                        feat = extract_features_from_window(ear_window)
                        feat_np = np.array(feat).reshape(1, -1)
                        probas = model.predict_proba(feat_np)[0]
                        current_prob = float(np.max(probas))
                        last_valid_prob = current_prob
                        current_status = "ENGAGED" if current_prob > 0.5 else "NOT ENGAGED"
                        
                        print_log(f"🧠 Inference: EAR samples={len(ear_window)}, Prob={current_prob:.3f}, Status={current_status}")
                        
                        if frame_count == 30:
                            cv2.imwrite("debug_frame.jpg", frame)
                            print_log("🖼️ Saved debug_frame.jpg")

                    elif len(ear_window) > 0:
                        # Use decay even without 3 samples
                        current_prob = max(0.05, last_valid_prob * 0.97)
                        current_status = "ENGAGED" if current_prob > 0.5 else "NOT ENGAGED"

                else:
                    # NO FACE: Use fallback values
                    current_prob = max(0.05, last_valid_prob * 0.97)
                    current_status = "NO FACE (DECAY)"
                    ear_avg = None

                # ✅ UPLOAD EVERY INFERENCE (not just once per second)
                if not SESSION_ACTIVE:
                    print_log("🛑 Session inactive. Stopping.")
                    break
                
                if current_status != "Collecting":
                    # Only upload if probability changed by more than 1%
                    if last_uploaded_prob is None or abs(current_prob - last_uploaded_prob) > 0.01:
                        print_log(f"🎯 UPLOAD TRIGGERED | Status: {current_status} | Prob: {current_prob:.3f}")
                        upload_point_background(SESSION_ID, current_prob, ear_avg, ts)
                        upload_count += 1
                        last_uploaded_prob = current_prob
                else:
                    # Log when still collecting
                    if frame_count % 100 == 0:
                        print_log(f"⏳ Still collecting EAR samples ({len(ear_window)}/3)")

                # Display (debugging only)
                if os.getenv("DISPLAY_ML_VIDEO") == "true":
                    color = (0, 255, 0) if current_prob > 0.5 else (0, 0, 255)
                    cv2.putText(frame, f"{current_status}", (20, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                    cv2.putText(frame, f"Conf: {current_prob:.2f}", (20, 100),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

                    cv2.imshow("Real-time Engagement", frame)

                    if cv2.waitKey(1) & 0xFF == 27:
                        print_log("🟢 [11] ESC key pressed")
                        break

            except Exception as e:
                print_log(f"❌ [ERROR] {type(e).__name__}: {e}")
                break

        print_log(f"🟢 [12] Loop exited: {frame_count} frames, {upload_count} uploads")

    # Keep process alive (but check if still active)
    print_log("🟢 Keeping ML process alive...")
    try:
        while SESSION_ACTIVE:
            time.sleep(1)
    except KeyboardInterrupt:
        print_log("🛑 ML process terminated by user")
    finally:
        graceful_exit(cap, logf)
        print_log("🟢 [14] Exit complete")
        close_debug_log()


if __name__ == "__main__":
    main()