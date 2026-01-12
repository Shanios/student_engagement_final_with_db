# backend/engagement.py
from datetime import datetime
from typing import List, Optional
from models import DeviceLog
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
    Get absolute path to realtime_engagement.py
    Searches multiple locations with fallback.
    
    Tries:
    1. D:\student_engagement\backend\engagement\realtime_engagement.py
    2. D:\student_engagement\engagement\realtime_engagement.py (symbolic)
    3. Current directory variations
    """
    
    current_file = Path(__file__).resolve()
    
    print(f"\n{'='*70}")
    print(f"🔍 SEARCHING FOR ML SCRIPT")
    print(f"   Current file: {current_file}")
    print(f"{'='*70}\n")
    
    # Build list of candidate paths
    candidates = []
    
    # 1. If in backend/engagement/, look in same directory
    if "engagement" in str(current_file):
        candidates.append(current_file.parent / "realtime_engagement.py")
    
    # 2. Backend directory
    backend_dir = Path(__file__).resolve().parent
    candidates.append(backend_dir / "realtime_engagement.py")
    candidates.append(backend_dir / "engagement" / "realtime_engagement.py")
    
    # 3. Parent of backend (project root)
    project_root = backend_dir.parent
    candidates.append(project_root / "engagement" / "realtime_engagement.py")
    candidates.append(project_root / "backend" / "engagement" / "realtime_engagement.py")
    
    # 4. Absolute paths
    candidates.append(Path("D:\\student_engagement\\backend\\engagement\\realtime_engagement.py"))
    candidates.append(Path("D:\\student_engagement\\engagement\\realtime_engagement.py"))
    
    # Search
    print("Searching locations:")
    for p in candidates:
        exists = p.exists()
        status = "✅ FOUND" if exists else "❌ not found"
        print(f"  {status}: {p}")
        
        if exists:
            resolved = p.resolve()
            print(f"\n✅ USING: {resolved}\n")
            print(f"{'='*70}\n")
            return str(resolved)
    
    # Not found - show all attempted paths
    error_msg = "ML script not found in any location:\n"
    for p in candidates:
        error_msg += f"  - {p}\n"
    
    print(f"❌ {error_msg}")
    print(f"{'='*70}\n")
    raise FileNotFoundError(error_msg)


def get_model_path():
    """
    Get absolute path to engagement_model.pkl
    Searches in multiple locations with fallback.
    """
    # Get the directory where THIS file (engagement.py) is located
    current_file = Path(__file__).resolve()
    print(f"📍 Current file: {current_file}")
    
    # Try to find backend directory
    backend_dir = None
    
    # If engagement.py is in backend/engagement/, go up 2 levels
    if current_file.parent.name == "engagement":
        backend_dir = current_file.parent.parent
    # If engagement.py is in backend/, go up 1 level
    elif current_file.parent.name == "backend":
        backend_dir = current_file.parent
    # Otherwise, assume we're in backend
    else:
        backend_dir = current_file.parent
    
    print(f"🔍 Backend dir: {backend_dir}")
    
    # Try multiple possible locations
    possible_paths = [
        backend_dir / "engagement" / "engagement_model.pkl",
        backend_dir / "engagement_model.pkl",
        current_file.parent / "engagement_model.pkl",
    ]
    
    print("🔍 Searching for model file:")
    for p in possible_paths:
        exists = p.exists()
        print(f"  - {p}: {'✅ EXISTS' if exists else '❌ NOT FOUND'}")
        if exists:
            print(f"✅ Using model at: {p}")
            return str(p)
    
    # If not found, show helpful error
    raise FileNotFoundError(
        f"Model not found. Searched locations:\n" +
        "\n".join([f"  - {p}" for p in possible_paths])
    )
@router.post("/start-ml")
def start_ml_process(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start ML process with correct environment setup"""
    
    print(f"\n{'='*80}")
    print(f"🧠 ML START REQUEST - Session {session_id}, Student {current_user.id}")
    print(f"{'='*80}\n")
    
    if current_user.role != "student":
        raise HTTPException(403, "Only students can start ML")
    
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(404, "Session not found")
    
    if session.ended_at is not None:
        raise HTTPException(400, "Session has already ended")
    
    from models import Attendance
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.student_id == current_user.id
    ).first()
    
    
    if not attendance:
        raise HTTPException(403, "Student has not joined this session")
    
    if session_id in ACTIVE_ML_PROCESSES:
        proc = ACTIVE_ML_PROCESSES[session_id]
        if proc.poll() is None:
            return {"status": "already_running", "session_id": session_id, "pid": proc.pid}
        else:
            del ACTIVE_ML_PROCESSES[session_id]
    
    try:
        import sys
        python_exe = sys.executable
        
        ml_script = get_ml_script_path()
        ml_token = create_access_token(data={"sub": str(current_user.id)})
        
        ml_script_abs = str(Path(ml_script).resolve())
        script_dir = str(Path(ml_script_abs).parent)
        
        cmd = [
            python_exe,
            ml_script_abs,
            f"--session-id={session_id}",
            f"--student-id={current_user.id}",
            f"--token={ml_token}",
            f"--backend=http://127.0.0.1:8000",
        ]
        
        print(f"📄 Script: {ml_script_abs}")
        print(f"📂 Working Dir: {script_dir}")
        print(f"🐍 Python: {python_exe}\n")
        
        # ✅ CRITICAL: Prepare environment with all necessary variables
        env = os.environ.copy()
        env["CAMERA_DEVICE_KEY"] = os.getenv("CAMERA_DEVICE_KEY", "default-device-key")
        env["PYTHONUNBUFFERED"] = "1"
        
        print(f"🔐 CAMERA_DEVICE_KEY: {env['CAMERA_DEVICE_KEY']}")
        print(f"🌍 PYTHONPATH: {env.get('PYTHONPATH', 'not set')}\n")
        
        # ✅ SPAWN WITH CORRECT WORKING DIRECTORY
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=script_dir,  # ✅ CRITICAL: Same directory as manual run
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
            start_new_session=True if os.name != 'nt' else False,
        )
        
        print(f"✅ Process spawned: PID {proc.pid}")
        print(f"⏳ Waiting 3 seconds to check for immediate crashes...\n")
        
        import time
        time.sleep(3)
        
        returncode = proc.poll()
        
        if returncode is not None:
            stdout, stderr = proc.communicate()
            
            print(f"\n{'='*80}")
            print(f"❌ ML PROCESS CRASHED - Exit Code: {returncode}")
            print(f"{'='*80}")
            print(f"\n📋 STDERR:\n{stderr if stderr else '(empty)'}")
            print(f"\n📋 STDOUT:\n{stdout if stdout else '(empty)'}")
            print(f"\n{'='*80}\n")
            
            # Also save to file
            with open("ml_crash_log.txt", "w") as f:
                f.write(f"Exit Code: {returncode}\n\n")
                f.write(f"STDERR:\n{stderr}\n\n")
                f.write(f"STDOUT:\n{stdout}\n")
            
            raise HTTPException(500, f"ML crashed with exit code {returncode}")
        
        ACTIVE_ML_PROCESSES[session_id] = proc
        
        print(f"{'='*80}")
        print(f"✅ ML PROCESS RUNNING")
        print(f"   PID: {proc.pid}")
        print(f"   Session: {session_id}")
        print(f"   Directory: {script_dir}")
        print(f"{'='*80}\n")
        
        return {
            "status": "started",
            "session_id": session_id,
            "pid": proc.pid,
            "message": "ML engagement tracking active"
        }
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}\n")
        raise HTTPException(500, str(e))
    except Exception as e:
        print(f"❌ Exception: {e}\n")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))
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
    """
    ✅ FIXED: End session AND auto-terminate all active students
    
    When teacher ends session:
    1. Mark session as ended
    2. Find all students still present (left_at IS NULL)
    3. Set their left_at = teacher_end_time
    4. Calculate their duration
    5. Commit everything in ONE transaction
    """
    
    print(f"\n{'='*80}")
    print(f"🛑 END SESSION REQUESTED")
    print(f"   Session ID: {session_id}")
    print(f"   Teacher ID: {current_user.id}")
    print(f"{'='*80}\n")
    
    # ✅ Authorization check
    if current_user.role != "teacher":
        print(f"❌ User {current_user.id} is not a teacher (role: {current_user.role})")
        raise HTTPException(status_code=403, detail="Only teacher can end session")

    # ✅ Get session
    print(f"📍 STEP 1: Fetching session {session_id}")
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        print(f"❌ Session {session_id} not found")
        raise HTTPException(status_code=404, detail="Session not found")

    print(f"✅ Session found: '{session.title}'")
    print(f"   Started at: {session.started_at}")
    print(f"   Current ended_at: {session.ended_at}")

    # ✅ Check if already ended
    if session.ended_at is not None:
        print(f"⚠️  Session already ended at {session.ended_at}")
        return {"status": "already_ended", "session_id": session_id}

    # ✅ Set session end time
    end_time = datetime.utcnow()
    session.ended_at = end_time
    print(f"✅ Session marked as ended at: {end_time}")

    # ✅ STEP 2: Auto-end all active students
    print(f"\n📍 STEP 2: Auto-terminating active students")
    active_students = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.left_at.is_(None)  # ✅ Only students still present
    ).all()

    print(f"   Found {len(active_students)} active students")

    for idx, attendance in enumerate(active_students, 1):
        # Calculate duration
        duration_seconds = int((end_time - attendance.joined_at).total_seconds())
        
        # Update student record
        attendance.left_at = end_time
        attendance.total_duration_seconds = duration_seconds
        
        print(f"   [{idx}] Student {attendance.student_id}:")
        print(f"        Joined: {attendance.joined_at}")
        print(f"        Left: {end_time}")
        print(f"        Duration: {duration_seconds} seconds ({duration_seconds/60:.1f} min)")

    # ✅ STEP 3: Commit everything in ONE transaction
    print(f"\n📍 STEP 3: Committing transaction...")
    try:
        db.add(session)  # Ensure session is tracked
        db.commit()  # ✅ ONE commit for session + all students
        print(f"✅ Transaction committed successfully!")
        print(f"   Session ended: 1 record")
        print(f"   Students terminated: {len(active_students)} records")
    except Exception as e:
        print(f"❌ Commit failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")

    print(f"{'='*80}\n")
    
    return {
        "status": "ended",
        "session_id": session_id,
        "ended_at": session.ended_at.isoformat(),
        "students_terminated": len(active_students),
        "message": f"Session ended. {len(active_students)} active students were auto-terminated."
    }
@router.post("/sessions/{session_id}/heartbeat")
def heartbeat(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✅ FIXED: Keep-alive endpoint for both teacher and student
    
    Purpose:
    - Teacher sends to keep session alive
    - Student sends to keep their connection active
    - ⚠️ DOES NOT create/modify attendance records
    
    Returns:
    - {"status": "alive"} if session is active
    - {"status": "ended"} if session has been ended
    """
    
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at is not None:
        print(f"📍 Heartbeat received for ended session {session_id}")
        return {"status": "ended"}

    # ✅ ONLY update session timestamp
    # ⚠️ Do NOT create/modify attendance here
    session.last_seen_at = datetime.utcnow()
    db.commit()

    print(f"💓 Heartbeat from {current_user.role} {current_user.id} for session {session_id}")
    
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
# @router.post("/attendance/join/{session_id}")
# def attend_session(
#     session_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     """Record student attendance in session"""
    
#     from models import Attendance
    
#     # Check if already marked
#     existing = db.query(Attendance).filter(
#         Attendance.session_id == session_id,
#         Attendance.student_id == current_user.id
#     ).first()
    
#     if existing:
#         return {"status": "already_joined", "session_id": session_id}
    
#     # Mark attendance
#     attendance = Attendance(
#         session_id=session_id,
#         student_id=current_user.id,
#         joined_at=datetime.utcnow()
#     )
    
    # db.add(attendance)
    # db.commit()
    
    # return {
    #     "status": "joined",
    #     "session_id": session_id,
    #     "message": "Attendance recorded"
    # }
# ---------- Student engagement stream (JWT – Student only) ----------
@router.post("/sessions/{session_id}/stream")
def stream_engagement(
    session_id: int,
    payload: PointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✅ FIXED: Stream engagement points during session.
    
    Requirements:
    1. Only students can stream
    2. Session must be active (not ended)
    3. Student must have joined (attendance exists)
    4. Student must be currently present (left_at IS NULL)
    
    Purpose:
    - Receive real-time engagement scores from ML model
    - Store as time-series data for analytics
    """
    
    # 1️⃣ Only students can send engagement
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can stream engagement")

    # 2️⃣ Validate session exists and is active
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at is not None:
        raise HTTPException(status_code=403, detail="Session already ended")

    # 3️⃣ ✅ FIXED: Ensure student has joined AND is still present
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

    # ✅ NEW: Check that student hasn't left
    if attendance.left_at is not None:
        raise HTTPException(
            status_code=403,
            detail="Student has already left this session"
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
    db.refresh(point)  # ✅ Optional: Refresh to get generated ID

    print(f"📊 Engagement point recorded: Session {session_id}, Student {current_user.id}, Score {payload.score:.3f}")

    return {
        "status": "ok",
        "point_id": point.id,
        "session_id": session_id,
        "timestamp": point.timestamp.isoformat(),
        "score": point.score
    }

# ---------- Camera upload (DEVICE AUTH – NO JWT) ----------
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/sessions/{session_id}/points", response_model=PointOut)
@limiter.limit("30/second")  # ✅ NEW: Max 30 uploads per second per IP
def add_point(
    
    session_id: int,
    payload: PointCreate,
    request: Request,  # ✅ NEW: For IP tracking
    db: Session = Depends(get_db),
    _: None = Depends(verify_camera_device),  # 🔐 device auth
): 

    # ✅ NEW: Log successful upload
    print("🔐 verify_camera_device CALLED")

    print("🔥 /points endpoint HIT")
    print(f"\n{'='*60}")
    print(f"📥 ENGAGEMENT POINT RECEIVED")
    print(f"   Session ID: {session_id}")
    print(f"   Score: {payload.score:.3f}")
    ear_str = f"{payload.ear:.3f}" if payload.ear is not None else "N/A"
    print(f"   EAR: {ear_str}")    
    print(f"   Timestamp: {payload.timestamp}")
    print(f"{'='*60}\n")
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
    db.add(device_log)  # ✅ ADD THIS
    db.commit()
  
    


 
    
    return PointOut(
        timestamp=point.timestamp,
        score=point.score,
        ear=point.ear
    )  # ✅ ADD THIS LINE

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
    - Includes engagement metrics + CORRECT student count
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
        # ✅ ENGAGEMENT POINTS (for avg score calculation)
        points = db.query(EngagementPoint).filter(
            EngagementPoint.session_id == session.id
        ).all()
        
        # ✅ CALCULATE SESSION DURATION (reusable)
        session_duration = (session.ended_at - session.started_at).total_seconds()
        
        # ✅ COUNT VALID STUDENTS (attended ≥15% of session)
        attendance_records = db.query(Attendance).filter(
            Attendance.session_id == session.id
        ).all()
        
        valid_students = 0
        for a in attendance_records:
            if not a.joined_at:
                continue
            
            if a.left_at:
                attended_seconds = (a.left_at - a.joined_at).total_seconds()
            else:
                attended_seconds = (session.ended_at - a.joined_at).total_seconds()
            
            attendance_percentage = (attended_seconds / session_duration) * 100
            
            if attendance_percentage >= 15:
                valid_students += 1
        
        # ✅ ENGAGEMENT SCORES (unchanged)
        scores = [p.score for p in points]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # ✅ BUILD RESPONSE (point_count → attendance_count)
        result.append({
            "id": session.id,
            "title": session.title,
            "subject": session.subject,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat(),
            "share_code": session.share_code,
            "duration_seconds": int(session_duration),
            "attendance_count": valid_students,  # ✅ CORRECT: Student count, not upload count
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



# ========== FIXED: Report Endpoint with Correct Duration ==========

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
    
    # ✅ FIX #1: Calculate duration correctly
    duration_seconds = int((session.ended_at - session.started_at).total_seconds())
    duration_minutes = duration_seconds // 60
    duration_secs = duration_seconds % 60
    duration_formatted = f"{duration_minutes}m {duration_secs}s"
    
    print(f"📊 Duration calculation:")
    print(f"   Started: {session.started_at}")
    print(f"   Ended: {session.ended_at}")
    print(f"   Delta: {duration_seconds} seconds")
    print(f"   Formatted: {duration_formatted}\n")
    
    # Fetch engagement points (may be empty)
    points = db.query(EngagementPoint).filter(
        EngagementPoint.session_id == session_id
    ).order_by(EngagementPoint.timestamp.asc()).all()
    
    # ✅ FIX #2: Handle empty data gracefully
    if not points:
        # Return empty report structure
        return {
            "session_id": session_id,
            "title": session.title,
            "subject": session.subject,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat(),
            "duration_minutes": duration_minutes,
            "duration_seconds": duration_seconds,
            "duration_formatted": duration_formatted,
            "generated_at": datetime.utcnow().isoformat(),
            
            "analytics": {
                "summary": {
                    "avg_score": 0.0,
                    "std_score": 0.0,
                    "min_score": 0.0,
                    "max_score": 0.0,
                    "total_points": 0,
                    "duration_seconds": duration_seconds,
                    "duration_minutes": duration_minutes,
                    "duration_formatted": duration_formatted,
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
    
    # ✅ FIX #3: Ensure duration is in analytics too
    analytics['summary']['duration_seconds'] = duration_seconds
    analytics['summary']['duration_minutes'] = duration_minutes
    analytics['summary']['duration_formatted'] = duration_formatted
    
    # Return structured report
    return {
        "session_id": session_id,
        "title": session.title,
        "subject": session.subject,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat(),
        "duration_minutes": duration_minutes,
        "duration_seconds": duration_seconds,
        "duration_formatted": duration_formatted,
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
@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only teacher can delete
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can delete sessions")

    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id,
        EngagementSession.teacher_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    # ✅ Soft delete
    session.is_deleted = True
    db.commit()

    return {
        "status": "deleted",
        "session_id": session_id
    }
