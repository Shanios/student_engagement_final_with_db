from sqlalchemy import Column, Integer, JSON,UniqueConstraint,String, DateTime, ForeignKey, Float, Boolean
from datetime import datetime

from database import Base


class User(Base):
    __tablename__ = "users"   # must match existing table

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="student")  # "student" or "teacher"


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    filename = Column(String, nullable=False)  # saved file name on disk
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, nullable=True)  # later link to User.id


class EngagementSession(Base):
    __tablename__ = "engagement_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    subject = Column(String)
    teacher_id = Column(Integer)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    share_code = Column(String, unique=True, index=True)
    # 🔒 AUTHORITY FLAGS (REQUIRED)
    is_locked = Column(Boolean, default=False)
    mute_students = Column(Boolean, default=False)
    disable_student_cameras = Column(Boolean, default=False)
    
class EngagementPoint(Base):
    __tablename__ = "engagement_points"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("engagement_sessions.id"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)  # when measured
    score = Column(Float, nullable=False)                  # engagement score 0–1 or 0/1
    ear = Column(Float, nullable=True)                     # optional raw EAR


class QuestionPaper(Base):
    __tablename__ = "question_papers"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    exam_type = Column(String, nullable=False)   # e.g. "internal", "university", "model"
    filename = Column(String, nullable=False)    # stored file name
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, nullable=True)    # teacher who uploaded


# ✅ NEW: Token security tables
class TokenBlacklist(Base):
    """Store revoked tokens to prevent reuse"""
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    revoked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # When token naturally expires


# ✅ NEW: Device audit trail
class DeviceLog(Base):
    """Audit trail for all device uploads"""
    __tablename__ = "device_logs"

    id = Column(Integer, primary_key=True, index=True)
    device_key_hash = Column(String, nullable=False)  # Hash of device key (not plaintext!)
    session_id = Column(Integer, ForeignKey("engagement_sessions.id"), nullable=True)
    client_ip = Column(String, nullable=True)  # Client IP address
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, nullable=False)  # "success", "invalid_key", "rate_limit", "failed_auth"
    details = Column(String, nullable=True)  # Additional info
    points_uploaded = Column(Integer, default=0)  # How many points in this request

    # ================== ATTENDANCE TRACKING ==================

class SessionAttendance(Base):
    """
    Tracks who joined a session and when.
    One row per user per session.
    """
    __tablename__ = "session_attendance"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(
        Integer,
        ForeignKey("engagement_sessions.id"),
        index=True,
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        index=True,
        nullable=False
    )

    role = Column(
        String,
        nullable=False
    )  # "teacher" or "student"

    joined_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    left_at = Column(
        DateTime,
        nullable=True
    )
class Attendance(Base):
    """
    Track student attendance with join/leave lifecycle.
    
    ✅ FIX B: UniqueConstraint prevents duplicate joins
    ✅ FIX C: left_at allows tracking presence duration
    ✅ FIX D: Single source of truth for attendance
    """
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True)
    
    session_id = Column(
        Integer, 
        ForeignKey("engagement_sessions.id"),
        nullable=False,
        index=True
    )
    
    student_id = Column(
        Integer, 
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    joined_at = Column(
        DateTime, 
        default=datetime.utcnow,
        nullable=False
    )
    
    # ✅ NEW: Track when student left
    left_at = Column(
        DateTime,
        nullable=True  # None = still present
    )

    # ✅ FIX B: Enforce one record per student per session
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_session_student"),
    )