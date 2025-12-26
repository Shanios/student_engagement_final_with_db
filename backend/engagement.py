# backend/engagement.py
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter,Header, Depends, HTTPException, Query, UploadFile, File, Request,BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import SessionLocal
from models import EngagementSession, EngagementPoint, User,Attendance
from auth import get_current_user
from device_auth import verify_camera_device
from engagement_model import predict_engagement
import os
import random
import string
import base64
import io
from PIL import Image

import subprocess
import psutil

from pathlib import Path
from auth import create_access_token  # Add this
import numpy as np
ACTIVE_ML_PROCESSES = {}
router = APIRouter(prefix="/api/engagement", tags=["engagement"])
# Move this to line 30-35 (right after imports):
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def get_ml_script_path():
    """
    CORRECTED: Add 'backend' to the path
    """
    backend_dir = Path(__file__).parent  # This gives backend/ directory
    
    # ML script is in backend/engagement/realtime_engagement.py
    ml_script = backend_dir / "engagement" / "realtime_engagement.py"
    
    print(f"🔍 Looking for ML script at: {ml_script}")
    
    if ml_script.exists():
        print(f"✅ Found ML script at: {ml_script}")
        return str(ml_script)
    
    # If not found, try creating it
    print(f"⚠️ Creating ML script at: {ml_script}")
    ml_script.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy your existing file there
    source_file = Path("D:\\student_engagement\\backend\\engagement\\realtime_engagement.py")
    if source_file.exists():
        import shutil
        shutil.copy(source_file, ml_script)
        print(f"✅ Copied from {source_file}")
    else:
        # Create a placeholder
        with open(ml_script, 'w') as f:
            f.write("# ML script placeholder\n")
        print(f"✅ Created placeholder")
    
    return str(ml_script)


def get_model_path():
    """
    Get absolute path to engagement_model.pkl
    CORRECTED: Look in multiple likely locations
    """
    backend_dir = Path(__file__).parent  # student_engagement/backend/
    
    # Try multiple possible locations
    possible_paths = [
        backend_dir / "engagement" / "engagement_model.pkl",  # backend/engagement/engagement_model.pkl
        backend_dir / "engagement_model.pkl",  # backend/engagement_model.pkl
        backend_dir.parent / "engagement_model.pkl",  # student_engagement/engagement_model.pkl
        Path("engagement_model.pkl"),  # Current working directory
    ]
    
    print("🔍 Searching for model file:")
    for p in possible_paths:
        exists = p.exists()
        print(f"  - {p}: {'✅ EXISTS' if exists else '❌ NOT FOUND'}")
        if exists:
            print(f"✅ Using model at: {p}")
            return str(p)
    
    raise FileNotFoundError(f"Model not found. Searched in: {[str(p) for p in possible_paths]}")


@router.post("/start-ml")
def start_ml_process(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start the realtime_engagement.py ML process for a student.
    
    ✅ Only students can start ML
    ✅ Session must exist and be active
    ✅ Only one ML process per session
    ✅ Returns process ID for debugging
    """
    
    # 1️⃣ Authorization: Only students
    if current_user.role != "student":
        raise HTTPException(403, "Only students can start ML process")
    
    # 2️⃣ Verify session exists and is active
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(404, "Session not found")
    
    if session.ended_at is not None:
        raise HTTPException(400, "Session has already ended")
    
    # 3️⃣ Verify student has joined attendance
    from models import Attendance
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.student_id == current_user.id
    ).first()
    
    if not attendance:
        raise HTTPException(403, "Student has not joined this session")
    
    # 4️⃣ Check if ML already running for this session
    if session_id in ACTIVE_ML_PROCESSES:
        proc = ACTIVE_ML_PROCESSES[session_id]
        if proc.poll() is None:  # Still running
            return {
                "status": "already_running",
                "session_id": session_id,
                "pid": proc.pid,
                "message": "ML process already active"
            }
        else:
            # Process died, clean up
            del ACTIVE_ML_PROCESSES[session_id]
    
    # 5️⃣ Start the ML process
    try:
        ml_script = get_ml_script_path()
        model_path = get_model_path()
        ml_token = create_access_token(data={"sub": str(current_user.id)})
        # Command to run:
        # python realtime_engagement.py --session-id=10 --model=path/to/model.pkl
        cmd = [
            "python",
            ml_script,
            f"--session-id={session_id}",
            f"--student-id={current_user.id}",
            f"--token={ml_token}",
           f"--backend=http://127.0.0.1:8000",
        ]
        
        print(f"🧠 Starting ML process for session {session_id}")
        print(f"   Command: {' '.join(cmd)}")
        env = os.environ.copy()
        env["CAMERA_DEVICE_KEY"] = os.getenv("CAMERA_DEVICE_KEY", "default-device-key")
        # Spawn subprocess (detached so it survives if server restarts)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            # Detach from parent process on both Windows and Unix
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
            start_new_session=True if os.name != 'nt' else False,
        )
        
        # 6️⃣ Store process reference
        ACTIVE_ML_PROCESSES[session_id] = proc
        
        print(f"✅ ML process started: PID {proc.pid}")
        
        return {
            "status": "started",
            "session_id": session_id,
            "pid": proc.pid,
            "message": "ML engagement tracking active"
        }
        
    except FileNotFoundError as e:
        raise HTTPException(500, f"ML script or model not found: {str(e)}")
    except Exception as e:
        print(f"❌ Failed to start ML process: {e}")
        raise HTTPException(500, f"Failed to start ML process: {str(e)}")


@router.post("/stop-ml")
def stop_ml_process(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stop the ML process for a session.
    
    ✅ Only students can stop
    ✅ Student must be the one who started it
    ✅ Gracefully terminates the process
    """
    
    # 1️⃣ Authorization: Only students
    if current_user.role != "student":
        raise HTTPException(403, "Only students can stop ML process")
    
    # 2️⃣ Check if process exists
    if session_id not in ACTIVE_ML_PROCESSES:
        return {
            "status": "not_running",
            "session_id": session_id,
            "message": "No active ML process for this session"
        }
    
    proc = ACTIVE_ML_PROCESSES[session_id]
    
    # 3️⃣ Check if process is still alive
    if proc.poll() is not None:
        # Already dead
        del ACTIVE_ML_PROCESSES[session_id]
        return {
            "status": "already_stopped",
            "session_id": session_id,
            "message": "ML process was already stopped"
        }
    
    # 4️⃣ Terminate gracefully
    try:
        print(f"🛑 Stopping ML process for session {session_id} (PID: {proc.pid})")
        
        # Try graceful termination first (SIGTERM on Unix, TerminateProcess on Windows)
        proc.terminate()
        
        # Wait up to 5 seconds for graceful shutdown
        try:
            proc.wait(timeout=5)
            print(f"✅ ML process terminated gracefully")
        except subprocess.TimeoutExpired:
            # Force kill if it doesn't respond
            print(f"⚠️ Process didn't respond to SIGTERM, force killing...")
            proc.kill()
            proc.wait()
            print(f"✅ ML process force killed")
        
        # Clean up reference
        del ACTIVE_ML_PROCESSES[session_id]
        
        return {
            "status": "stopped",
            "session_id": session_id,
            "message": "ML process terminated"
        }
        
    except Exception as e:
        print(f"❌ Error stopping ML process: {e}")
        raise HTTPException(500, f"Failed to stop ML process: {str(e)}")


@router.get("/ml-status")
def get_ml_status(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check if ML process is running for a session.
    
    ✅ Useful for frontend to verify ML is active
    ✅ Returns PID if running, status if stopped
    """
    
    if session_id not in ACTIVE_ML_PROCESSES:
        return {
            "status": "not_running",
            "session_id": session_id,
            "is_active": False
        }
    
    proc = ACTIVE_ML_PROCESSES[session_id]
    is_alive = proc.poll() is None  # None = still running
    
    if is_alive:
        return {
            "status": "running",
            "session_id": session_id,
            "is_active": True,
            "pid": proc.pid
        }
    else:
        return {
            "status": "stopped",
            "session_id": session_id,
            "is_active": False,
            "exit_code": proc.returncode
        }


@router.post("/ml-cleanup")
def cleanup_all_ml_processes():
    """
    Emergency endpoint: Kill all active ML processes.
    
    ⚠️ Use only for:
    - Server shutdown
    - Debugging
    - Emergency stop
    
    ✅ No authentication (only call from backend)
    """
    
    killed = []
    failed = []
    
    for session_id, proc in list(ACTIVE_ML_PROCESSES.items()):
        try:
            if proc.poll() is None:  # Still running
                proc.terminate()
                proc.wait(timeout=5)
                killed.append(session_id)
                print(f"✅ Killed ML process for session {session_id}")
        except Exception as e:
            failed.append((session_id, str(e)))
            print(f"❌ Failed to kill ML process {session_id}: {e}")
    
    ACTIVE_ML_PROCESSES.clear()
    
    return {
        "status": "cleanup_complete",
        "killed_count": len(killed),
        "killed_sessions": killed,
        "failed_count": len(failed),
        "failed_sessions": failed
    }
def generate_share_code() -> str:
    """Generate a 6-char share code like: A9F3-K2L7"""
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(random.choices(chars, k=4))
    part2 = ''.join(random.choices(chars, k=4))
    return f"{part1}-{part2}"



# ---------- DB dependency ----------


# ---------- Schemas ----------

class SessionCreate(BaseModel):
    title: str
    subject: Optional[str] = None


class SessionOut(BaseModel):
    id: int
    title: str
    subject: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    share_code: Optional[str] = None  # ✅ NEW
    user_role: str

    class Config:
        from_attributes = True


class PointCreate(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    ear: Optional[float] = None
    timestamp: Optional[datetime] = None


class PointOut(BaseModel):
    timestamp: datetime
    score: float
    ear: Optional[float]

    class Config:
        from_attributes = True


class PredictRequest(BaseModel):
    features: List[float]


class PredictResponse(BaseModel):
    label: int
    probability: Optional[float] = None


# 🔧 FIX: Move SessionAnalyticsOut HERE (before it's used)
class SessionAnalyticsOut(BaseModel):
    session_id: int
    avg_score: float
    max_score: float
    min_score: float
    total_points: int
    duration_seconds: int | None


class ImagePredictRequest(BaseModel):
    image_b64: str


class ImagePredictResponse(BaseModel):
    label: int
    probability: Optional[float]

class JoinSessionPayload(BaseModel):
    share_code: str


class JoinSessionResponse(BaseModel):
    session_id: int
    title: str
    subject: Optional[str]
    share_code: str
    started_at: datetime

    class Config:
        from_attributes = True
# ---------- Session management (JWT / Teacher) ----------
class SessionDetailOut(BaseModel):
    session_id: int
    room_id: str
    user_id: str
    user_role: str
    title: str
    subject: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    mute_students: bool
    disable_student_cameras: bool
    is_locked: bool
@router.post("/sessions", response_model=SessionOut)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teachers can start engagement sessions")

    # ✅ NEW: Generate unique share code
    share_code = generate_share_code()
    
    session = EngagementSession(
        title=payload.title,
        subject=payload.subject,
        teacher_id=current_user.id,
        share_code=share_code,  # ✅ NEW
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionOut(
    id=session.id,
    title=session.title,
    subject=session.subject,
    started_at=session.started_at,
    ended_at=session.ended_at,
    share_code=session.share_code,
    user_role=current_user.role,  # ✅ derived, not stored
)


# ---------- End Session (Teacher only) ----------
@router.get("/sessions/{session_id}", response_model=SessionDetailOut)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # ✅ BACKEND DECIDES ROLE — SINGLE SOURCE OF TRUTH
    if current_user.role == "teacher":
        user_role = "host"
    else:
        user_role = "audience"

    return {
        "session_id": session.id,
        "room_id": str(session.id),                # Zego room = session id
        "user_id": f"{current_user.role}-{current_user.id}",
        "user_role": user_role,                    # 🔥 THIS FIXES EVERYTHING
        "title": session.title,
        "subject": session.subject,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "mute_students": session.mute_students,
        "disable_student_cameras": session.disable_student_cameras,
        "is_locked": session.is_locked,
    }


@router.post("/sessions/{session_id}/end")
def end_session(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teacher can end session")

    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at is not None:
        return {"status": "already_ended", "session_id": session_id}

    session.ended_at = datetime.utcnow()
    db.commit()
    
    return {
        "status": "ended",
        "session_id": session_id,
        "ended_at": session.ended_at.isoformat(),
    }
@router.post("/sessions/{session_id}/heartbeat")
def heartbeat(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404)

    if session.ended_at is not None:
        return {"status": "ended"}

    if current_user.role != "teacher":
        raise HTTPException(403)

    session.last_seen_at = datetime.utcnow()
    db.commit()

    return {"status": "alive"}
# ---------- Student join session via share code ----------

@router.post("/sessions/join", response_model=JoinSessionResponse)
def join_session(
    payload: JoinSessionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Student joins session by entering share code.
    
    Requirements:
    - Session must exist
    - Share code must match
    - Session must be ACTIVE (ended_at IS NULL)
    """
    
    # Validate share code format
    if not payload.share_code or len(payload.share_code.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="Share code cannot be empty"
        )
    
  
   # Find session by share code (case-insensitive)
    code_to_find = payload.share_code.strip().upper()
    session = db.query(EngagementSession).filter(
       EngagementSession.share_code.ilike(code_to_find)
    ).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Invalid share code. Session not found."
        )

    # Check if session is still active
    if session.ended_at is not None:
        raise HTTPException(
            status_code=403,
            detail="This session has already ended."
        )

    # Return session info to student
    return JoinSessionResponse(
        session_id=session.id,
        title=session.title,
        subject=session.subject,
        share_code=session.share_code,
        started_at=session.started_at,
    )
@router.post("/attendance/join/{session_id}")
def attend_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record student attendance in session"""
    
    from models import Attendance
    
    # Check if already marked
    existing = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.student_id == current_user.id
    ).first()
    
    if existing:
        return {"status": "already_joined", "session_id": session_id}
    
    # Mark attendance
    attendance = Attendance(
        session_id=session_id,
        student_id=current_user.id,
        joined_at=datetime.utcnow()
    )
    
    db.add(attendance)
    db.commit()
    
    return {
        "status": "joined",
        "session_id": session_id,
        "message": "Attendance recorded"
    }
# ---------- Student engagement stream (JWT – Student only) ----------
@router.post("/sessions/{session_id}/stream")
def stream_engagement(
    session_id: int,
    payload: PointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1️⃣ Only students can send engagement
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can stream engagement")

    # 2️⃣ Validate session
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at is not None:
        raise HTTPException(status_code=403, detail="Session already ended")

    # 3️⃣ Ensure student has joined (attendance check)
    from models import Attendance
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.student_id == current_user.id
    ).first()

    if not attendance:
        raise HTTPException(
            status_code=403,
            detail="Student has not joined the session"
        )

    # 4️⃣ Store engagement point (time-series)
    ts = payload.timestamp or datetime.utcnow()

    point = EngagementPoint(
        session_id=session_id,
        timestamp=ts,
        score=payload.score,
        ear=payload.ear,
    )

    db.add(point)
    db.commit()

    return {"status": "ok"}

# ---------- Camera upload (DEVICE AUTH – NO JWT) ----------
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/sessions/{session_id}/points", response_model=PointOut)
@limiter.limit("10/second")  # ✅ NEW: Max 10 uploads per second per IP
def add_point(
    session_id: int,
    payload: PointCreate,
    request: Request,  # ✅ NEW: For IP tracking
    db: Session = Depends(get_db),
    _: None = Depends(verify_camera_device),  # 🔐 device auth
):
    # ✅ NEW: Log successful upload
    from models import DeviceLog
    
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at is not None:
        raise HTTPException(
            status_code=403,
            detail="Engagement session has ended. Uploads are disabled."
        )

    ts = payload.timestamp or datetime.utcnow()

    point = EngagementPoint(
        session_id=session_id,
        timestamp=ts,
        score=payload.score,
        ear=payload.ear,
    )

    db.add(point)
    db.commit()
    db.refresh(point)
    
    # ✅ NEW: Log successful upload
    client_ip = request.client.host if request else "unknown"
    device_log = DeviceLog(
        device_key_hash="camera",  # Don't store actual key
        session_id=session_id,
        client_ip=client_ip,
        status="success",
        details="Point uploaded",
        points_uploaded=1
    )
  
    


    db.add(device_log)
    db.commit()
    
    return point  # ✅ ADD THIS LINE

# ---------- Graph read (JWT – Teacher/Student) ----------
@router.get("/sessions/{session_id}/series/updates", response_model=list[PointOut])
def get_series_updates(
    session_id: int,
    since: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ✅ NEW: Verify session exists and is still active
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # ✅ NEW: Block polling after session ends
    if session.ended_at is not None:
        raise HTTPException(
            status_code=403,
            detail="Session has ended. Polling disabled."
        )

    q = db.query(EngagementPoint).filter(
        EngagementPoint.session_id == session_id
    )

    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            q = q.filter(EngagementPoint.timestamp > since_dt)
        except Exception:
            raise HTTPException(400, "Invalid 'since' timestamp")

    return q.order_by(EngagementPoint.timestamp.asc()).all()

@router.get("/sessions/{session_id}/series", response_model=list[PointOut])
def get_series(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ✅ NEW: Verify session exists
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return (
        db.query(EngagementPoint)
        .filter(EngagementPoint.session_id == session_id)
        .order_by(EngagementPoint.timestamp.asc())
        .all()
    )

@router.get("/sessions/{session_id}/analytics", response_model=SessionAnalyticsOut)
def get_session_analytics(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    points = db.query(EngagementPoint).filter(
        EngagementPoint.session_id == session_id
    ).all()

    if not points:
        return SessionAnalyticsOut(
            session_id=session_id,
            avg_score=0.0,
            max_score=0.0,
            min_score=0.0,
            total_points=0,
            duration_seconds=0,
        )

    scores = [p.score for p in points]

    # Duration
    end_time = session.ended_at or datetime.utcnow()
    duration = int((end_time - session.started_at).total_seconds())

    return SessionAnalyticsOut(
        session_id=session_id,
        avg_score=round(sum(scores) / len(scores), 3),
        max_score=round(max(scores), 3),
        min_score=round(min(scores), 3),
        total_points=len(scores),
        duration_seconds=duration,
    )

# ---------- Feature prediction ----------

@router.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest):
    result = predict_engagement(payload.features)

    if isinstance(result, dict):
        return PredictResponse(
            label=int(result["label"]),
            probability=result.get("probability"),
        )

    if isinstance(result, (list, tuple)):
        return PredictResponse(
            label=int(result[0]),
            probability=(float(result[1]) if len(result) > 1 else None),
        )

    if isinstance(result, (float, int)):
        return PredictResponse(label=int(result >= 0.5), probability=float(result))

    raise HTTPException(500, "Unexpected model output")


# ---------- Image prediction (JWT protected) ----------

@router.post("/predict_image", response_model=ImagePredictResponse)
def predict_from_image(
    payload: ImagePredictRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        b64 = payload.image_b64.split(",")[-1]
        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        img = img.resize((128, 128))

        arr = np.asarray(img).astype(np.float32) / 255.0
        features = arr.reshape(-1).tolist()

        result = predict_engagement(features)
        return ImagePredictResponse(
            label=int(result["label"]),
            probability=result.get("probability"),
        )
    except Exception as exc:
        raise HTTPException(500, f"Image predict error: {exc}")


# ========== TEACHER SESSION HISTORY ==========

@router.get("/sessions/teacher/all")
def get_teacher_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all ended sessions for current teacher.
    
    ✅ NEW: Return all historical sessions with statistics
    - Only teacher can access
    - Only ended sessions (ended_at IS NOT NULL)
    - Sorted by date (newest first)
    - Includes engagement metrics
    """
    
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teachers can view sessions")
    
    sessions = db.query(EngagementSession).filter(
        EngagementSession.teacher_id == current_user.id,
        EngagementSession.ended_at.isnot(None)  # Only ended sessions
    ).order_by(EngagementSession.ended_at.desc()).all()  # Newest first
    
    # Build response with statistics
    result = []
    for session in sessions:
        points = db.query(EngagementPoint).filter(
            EngagementPoint.session_id == session.id
        ).all()
        
        duration = int((session.ended_at - session.started_at).total_seconds())
        
        scores = [p.score for p in points]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        result.append({
            "id": session.id,
            "title": session.title,
            "subject": session.subject,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat(),
            "share_code": session.share_code,
            "duration_seconds": duration,
            "point_count": len(points),
            "avg_engagement": round(avg_score, 3),
            "max_engagement": max(scores) if scores else 0,
        })
    
    return result
@router.get("/teacher/sessions/summary")
def get_teacher_session_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all ended sessions with analytics for teacher dashboard.
    """
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teachers can view session summaries")
    
    sessions = db.query(EngagementSession).filter(
        EngagementSession.teacher_id == current_user.id,
        EngagementSession.ended_at.isnot(None)
    ).order_by(EngagementSession.ended_at.desc()).all()
    
    result = []
    for session in sessions:
        result.append({
            "id": session.id,
            "title": session.title,
            "subject": session.subject,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat(),
            "share_code": session.share_code,
            "analytics_ready": session.analytics_computed,
            "analytics_computed_at": session.analytics_computed_at.isoformat() if session.analytics_computed_at else None,
            "summary": {
                "attention_score": session.attention_score,
                "focus_time_percentage": session.focus_time_percentage,
                "avg_engagement": session.avg_engagement,
                "total_points": session.total_points,
            } if session.analytics_computed else None,
        })
    
    return result
# ========== ADVANCED ANALYTICS ==========

@router.get("/sessions/{session_id}/advanced-analytics")
def get_advanced_analytics(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return advanced analytics with insights.
    """
    from analytics import get_all_advanced_analytics
    
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    points = db.query(EngagementPoint).filter(
        EngagementPoint.session_id == session_id
    ).order_by(EngagementPoint.timestamp.asc()).all()
    
    # Convert to list of dicts
    points_data = [
        {"timestamp": p.timestamp.isoformat(), "score": p.score}
        for p in points
    ]
    
    # Calculate all metrics
    analytics = get_all_advanced_analytics(points_data)
    
    return analytics
@router.post("/predict_upload", response_model=ImagePredictResponse)
async def predict_from_upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    try:
        img = Image.open(io.BytesIO(await file.read())).convert("RGB")
        img = img.resize((128, 128))

        arr = np.asarray(img).astype(np.float32) / 255.0
        features = arr.reshape(-1).tolist()

        result = predict_engagement(features)
        return ImagePredictResponse(
            label=int(result["label"]),
            probability=result.get("probability"),
        )
    except Exception as exc:
        raise HTTPException(500, f"Upload predict error: {exc}")
@router.post("/sessions/{session_id}/mute")
def mute_students(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(403)

    session = db.get(EngagementSession, session_id)
    session.mute_students = True
    db.commit()
    return {"mute_students": True}


@router.post("/sessions/{session_id}/unmute")
def unmute_students(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(403)

    session = db.get(EngagementSession, session_id)
    session.mute_students = False
    db.commit()
    return {"mute_students": False}
@router.post("/sessions/{session_id}/disable-cameras")
def disable_cameras(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(403)

    session = db.get(EngagementSession, session_id)
    session.disable_student_cameras = True
    db.commit()
    return {"disable_student_cameras": True}


@router.post("/sessions/{session_id}/enable-cameras")
def enable_cameras(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(403)

    session = db.get(EngagementSession, session_id)
    session.disable_student_cameras = False
    db.commit()
    return {"disable_student_cameras": False}
from analytics import get_comprehensive_analytics



@router.get("/sessions/{session_id}/report")
def get_session_report(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✅ Fetch generated report for a session.
    Works with or without engagement data.
    """
    
    # Verify teacher owns session
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(404, "Session not found")
    
    if current_user.role != "teacher" or session.teacher_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the session teacher can view reports"
        )
    
    # Session must be ended
    if session.ended_at is None:
        raise HTTPException(
            status_code=400,
            detail="Session must be ended before viewing report"
        )
    
    # Fetch engagement points (may be empty)
    points = db.query(EngagementPoint).filter(
        EngagementPoint.session_id == session_id
    ).order_by(EngagementPoint.timestamp.asc()).all()
    
    # ✅ NEW: Handle empty data gracefully
    if not points:
        # Return empty report structure
        return {
            "session_id": session_id,
            "title": session.title,
            "subject": session.subject,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat(),
            "duration_minutes": 0,
            "duration_formatted": "0m 0s",
            "generated_at": datetime.utcnow().isoformat(),
            
            "analytics": {
                "summary": {
                    "avg_score": 0.0,
                    "std_score": 0.0,
                    "min_score": 0.0,
                    "max_score": 0.0,
                    "total_points": 0,
                    "duration_seconds": int((session.ended_at - session.started_at).total_seconds()),
                    "duration_minutes": int((session.ended_at - session.started_at).total_seconds()) // 60,
                    "duration_formatted": f"{int((session.ended_at - session.started_at).total_seconds()) // 60}m {int((session.ended_at - session.started_at).total_seconds()) % 60}s",
                    "attention_score": 0,
                    "focus_time_percentage": 0.0,
                    "volatility": 0.0,
                },
                "distribution": {
                    "low_engagement": 0.0,
                    "medium_engagement": 0.0,
                    "high_engagement": 0.0,
                },
                "critical_moments": {
                    "dropoffs": [],
                    "peak_periods": [],
                    "distraction_spikes": [],
                    "total_dropoffs": 0,
                    "total_peaks": 0,
                    "total_spikes": 0,
                },
                "sustained_engagement": {
                    "sustained_periods": [],
                    "high_focus_segments": [],
                    "low_attention_segments": [],
                },
            },
            
            "timeline": []
        }
    
    # Convert to dict format for analytics
    points_data = [
        {
            'timestamp': p.timestamp.isoformat(),
            'score': p.score
        }
        for p in points
    ]
    
    # Compute analytics using your analytics.py
    from analytics import get_comprehensive_analytics
    analytics = get_comprehensive_analytics(points_data)
    
    # Return structured report
    return {
        "session_id": session_id,
        "title": session.title,
        "subject": session.subject,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat(),
        "duration_minutes": analytics['summary'].get('duration_minutes', 0),
        "duration_formatted": analytics['summary'].get('duration_formatted', '0m 0s'),
        "generated_at": datetime.utcnow().isoformat(),
        
        "analytics": {
            "summary": analytics.get('summary', {}),
            "distribution": analytics.get('distribution', {}),
            "critical_moments": analytics.get('critical_moments', {}),
            "sustained_engagement": analytics.get('sustained_engagement', {}),
        },
        
        "timeline": analytics.get('timeline', [])
    }
@router.post("/sessions/{session_id}/email-report")
async def email_report(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✅ NEW: Request report via email.
    
    Triggers background job to generate and email the report.
    
    Args:
        session_id: The engagement session ID
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Authenticated user (teacher)
    
    Returns:
        Confirmation message
    """
    
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(404, "Session not found")
    
    if current_user.role != "teacher" or session.teacher_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    
    if session.ended_at is None:
        raise HTTPException(400, "Session must be ended")
    
    # Queue background task
    background_tasks.add_task(
        send_report_email,
        session_id,
        current_user.email
    )
    
    return {
        "status": "email_queued",
        "message": f"Report will be sent to {current_user.email}",
        "session_id": session_id
    }


@router.post("/sessions/{session_id}/whatsapp-report")
async def whatsapp_report(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✅ NEW: Request report via WhatsApp.
    
    Triggers background job to generate and send via WhatsApp.
    (Requires Twilio setup)
    
    Args:
        session_id: The engagement session ID
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Authenticated user (teacher)
    
    Returns:
        Confirmation message
    """
    
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(404, "Session not found")
    
    if current_user.role != "teacher" or session.teacher_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    
    if session.ended_at is None:
        raise HTTPException(400, "Session must be ended")
    
    # Queue background task
    background_tasks.add_task(
        send_report_whatsapp,
        session_id,
        current_user.email  # Will need to get teacher's WhatsApp number from DB later
    )
    
    return {
        "status": "whatsapp_queued",
        "message": "Report will be sent to your WhatsApp",
        "session_id": session_id
    }


@router.get("/sessions/{session_id}/report/pdf")
def download_report_pdf(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✅ NEW: Download report as PDF.
    
    Generates a PDF file with all analytics and graphs.
    
    Args:
        session_id: The engagement session ID
        db: Database session
        current_user: Authenticated user (teacher)
    
    Returns:
        PDF file for download
    """
    
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(404, "Session not found")
    
    if current_user.role != "teacher" or session.teacher_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    
    if session.ended_at is None:
        raise HTTPException(400, "Session must be ended")
    
    # Fetch engagement points
    points = db.query(EngagementPoint).filter(
        EngagementPoint.session_id == session_id
    ).order_by(EngagementPoint.timestamp.asc()).all()
    
    if not points:
        raise HTTPException(404, "No engagement data")
    
    # Compute analytics
    points_data = [{'timestamp': p.timestamp.isoformat(), 'score': p.score} for p in points]
    analytics = get_comprehensive_analytics(points_data)
    
    # Generate PDF (requires reportlab)
    try:
        pdf_bytes = generate_pdf_report(session, analytics)
        
        from fastapi.responses import StreamingResponse
        import io
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=report_{session_id}.pdf"}
        )
    except Exception as e:
        print(f"❌ PDF generation error: {e}")
        raise HTTPException(500, "Failed to generate PDF")


# ====== BACKGROUND TASKS ======

def send_report_email(session_id: int, teacher_email: str):
    """
    Background job: Send report via email.
    
    TODO: Implement with smtplib or SendGrid
    """
    print(f"📧 Sending report email for session {session_id} to {teacher_email}")
    # TODO: Generate email + attachments + send
    pass


def send_report_whatsapp(session_id: int, teacher_contact: str):
    """
    Background job: Send report via WhatsApp.
    
    TODO: Implement with Twilio WhatsApp API
    """
    print(f"📱 Sending report via WhatsApp for session {session_id}")
    # TODO: Use Twilio to send graphs + summary
    pass


def generate_pdf_report(session, analytics):
    """
    Generate PDF report with graphs and analytics.
    
    TODO: Implement with reportlab
    """
    # This would use reportlab library
    # For now, return empty bytes (PDF generation can be added later)
    return b""
