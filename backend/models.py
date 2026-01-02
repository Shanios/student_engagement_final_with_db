from sqlalchemy import Column, Integer, JSON, UniqueConstraint, String, DateTime, ForeignKey, Float, Boolean
from datetime import datetime

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="student")  # "student" or "teacher"


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, nullable=True)


class EngagementSession(Base):
    __tablename__ = "engagement_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    subject = Column(String)
    teacher_id = Column(Integer)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    share_code = Column(String, unique=True, index=True)
    last_seen_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    
    # 🔒 AUTHORITY FLAGS
    is_locked = Column(Boolean, default=False)
    mute_students = Column(Boolean, default=False)
    disable_student_cameras = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

class EngagementPoint(Base):
    __tablename__ = "engagement_points"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("engagement_sessions.id"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    score = Column(Float, nullable=False)
    ear = Column(Float, nullable=True)


class QuestionPaper(Base):
    __tablename__ = "question_papers"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    exam_type = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, nullable=True)


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    revoked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class DeviceLog(Base):
    __tablename__ = "device_logs"

    id = Column(Integer, primary_key=True, index=True)
    device_key_hash = Column(String, nullable=False)
    session_id = Column(Integer, ForeignKey("engagement_sessions.id"), nullable=True)
    client_ip = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, nullable=False)
    details = Column(String, nullable=True)
    points_uploaded = Column(Integer, default=0)


# ==================== ATTENDANCE TRACKING ====================

class Attendance(Base):
    """
    ✅ SINGLE SOURCE OF TRUTH for attendance.
    
    One row per student per session.
    - UniqueConstraint prevents duplicates
    - left_at tracks presence state (None = present, datetime = left)
    - Models state, not events
    
    Key behaviors:
    1. First join: Create row with joined_at, left_at=None
    2. Rejoin: Update left_at=None (mark as present again)
    3. Leave: Set left_at=datetime.utcnow()
    4. Count present: WHERE left_at IS NULL
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
    
    # ✅ Tracks presence: None = present, datetime = left
    left_at = Column(
        DateTime,
        nullable=True
    )
    total_duration_seconds = Column(Integer, default=0)
    # ✅ Enforce one record per student per session
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_session_student"),
    )