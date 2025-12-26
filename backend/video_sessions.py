from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import os, time, json, base64, hmac, hashlib
from dotenv import load_dotenv
from datetime import datetime

from database import SessionLocal
from models import EngagementSession, User
from auth import get_current_user

load_dotenv()

router = APIRouter(prefix="/api/video", tags=["video"])

ZEGOCLOUD_APP_ID = int(os.getenv("ZEGOCLOUD_APP_ID"))
ZEGOCLOUD_SERVER_SECRET = os.getenv("ZEGOCLOUD_SERVER_SECRET")

if not ZEGOCLOUD_SERVER_SECRET or len(ZEGOCLOUD_SERVER_SECRET) != 32:
    raise RuntimeError("ZEGOCLOUD_SERVER_SECRET must be exactly 32 characters")


# ======================
# DB DEPENDENCY
# ======================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======================
# TOKEN GENERATION (UNCHANGED)
# ======================
def generate_kit_token(app_id: int, user_id: str, room_id: str) -> str:
    ctime = int(time.time())
    expire = ctime + 3600

    payload = {
        "app_id": app_id,
        "user_id": user_id,
        "room_id": room_id,
        "ctime": ctime,
        "expire": expire,
    }

    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = base64.b64encode(payload_json.encode()).decode()

    signature = hmac.new(
        ZEGOCLOUD_SERVER_SECRET.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).digest()

    signature_b64 = base64.b64encode(signature).decode()

    return f"{payload_b64}.{signature_b64}"


# ======================
# KIT TOKEN API (UNCHANGED)
# ======================
@router.get("/kit-token")
def get_kit_token(
    session_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at:
        raise HTTPException(status_code=403, detail="Session has ended")

    # 🔒 UPDATE G.1 — ROOM LOCK CHECK
    if getattr(session, "is_locked", False):
        raise HTTPException(
            status_code=403,
            detail="Class is locked by teacher"
        )

    room_id = str(session_id)
    user_id = f"{current_user.role}-{current_user.id}"

    token = generate_kit_token(
        ZEGOCLOUD_APP_ID,
        user_id,
        room_id
    )

    return {
        "kitToken": token,
        "room_id": room_id,
        "user_id": user_id,
          "user_role": "host" if current_user.role == "teacher" else "audience",  
        "app_id": ZEGOCLOUD_APP_ID,
    }


# ==================================================
# =============== UPDATE G — AUTHORITY ==============
# ==================================================

# 🔒 G.2 — LOCK / UNLOCK ROOM
@router.post("/sessions/{session_id}/lock")
def lock_room(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can lock room")

    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    session.is_locked = True
    db.commit()

    return {"status": "locked", "session_id": session_id}


@router.post("/sessions/{session_id}/unlock")
def unlock_room(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can unlock room")

    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    session.is_locked = False
    db.commit()

    return {"status": "unlocked", "session_id": session_id}


# 🔇 G.3 — MUTE ALL STUDENTS (LOGICAL FLAG)
@router.post("/sessions/{session_id}/mute-all")
def mute_all_students(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can mute students")

    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    session.mute_students = True
    db.commit()

    return {"status": "students_muted"}


# 📷 G.4 — DISABLE STUDENT CAMERAS
@router.post("/sessions/{session_id}/disable-cameras")
def disable_student_cameras(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can control cameras")

    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    session.disable_student_cameras = True
    db.commit()

    return {"status": "student_cameras_disabled"}
