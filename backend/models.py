from sqlalchemy import (
    Column, Integer, String, DateTime,
    ForeignKey, Float, Boolean,
    UniqueConstraint, Index
)
from sqlalchemy.sql import func
from datetime import datetime, timezone
from database import Base

# ==================== USERS ====================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="student", nullable=False)


# ==================== NOTES ====================

class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    filename = Column(String(255), nullable=False)

    uploaded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)


# ==================== ENGAGEMENT ====================

class EngagementSession(Base):
    __tablename__ = "engagement_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)

    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    ended_at = Column(DateTime(timezone=True), nullable=True)
    share_code = Column(String(255), unique=True, index=True, nullable=False)

    last_seen_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True
    )

    is_locked = Column(Boolean, default=False)
    mute_students = Column(Boolean, default=False)
    disable_student_cameras = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)


class EngagementPoint(Base):
    __tablename__ = "engagement_points"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("engagement_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    score = Column(Float, nullable=False)
    ear = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_engagement_points_session", "session_id"),
        Index("idx_engagement_points_timestamp", "timestamp"),
    )


# ==================== QUESTION PAPERS ====================

class QuestionPaper(Base):
    __tablename__ = "question_papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False)
    exam_type = Column(String(100), nullable=False)
    filename = Column(String(255), nullable=False)

    uploaded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)


# ==================== TOKEN BLACKLIST ====================

class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    revoked_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)


# ==================== DEVICE LOGS ====================

class DeviceLog(Base):
    __tablename__ = "device_logs"

    id = Column(Integer, primary_key=True, index=True)
    device_key_hash = Column(String(255),  index=True, nullable=False)
    session_id = Column(Integer, ForeignKey("engagement_sessions.id"))
    client_ip = Column(String(50))
    status = Column(String(50), nullable=False)

    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    details = Column(String)
    points_uploaded = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('device_key_hash', 'session_id', name='uq_device_session'),
        Index("idx_device_logs_device_key_hash", "device_key_hash"),
        Index("idx_device_logs_session_id", "session_id"),
    )
# ==================== ATTENDANCE ====================

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True)

    session_id = Column(
        Integer,
        ForeignKey("engagement_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    joined_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    left_at = Column(DateTime(timezone=True), nullable=True)
    total_duration_seconds = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_session_student"),
        Index("idx_attendance_session", "session_id"),
        Index("idx_attendance_student", "student_id"),
    )
