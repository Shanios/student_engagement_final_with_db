from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import csv
from io import StringIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from dotenv import load_dotenv

from database import SessionLocal
from models import EngagementSession, User, Attendance
from auth import get_current_user
from fastapi.responses import StreamingResponse

load_dotenv()

# ==================== EMAIL CONFIGURATION ====================
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

if not SENDER_EMAIL or not SENDER_PASSWORD:
    print("⚠️ WARNING: Email credentials not configured in .env")

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== EMAIL SENDING FUNCTION ====================

def send_attendance_email(teacher_email: str, session_title: str, attendance_data: list):
    """Send attendance report to teacher's email."""
    try:
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Student ID", "Email", "Joined At", "Left At", "Duration (minutes)", "Status"])
        
        for item in attendance_data:
            writer.writerow([
                item["id"],
                item["email"],
                item["joined_at"],
                item["left_at"],
                item.get("duration_min", "-"),
                item["status"]
            ])
        
        csv_content = output.getvalue()
        
        # Create email message
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = teacher_email
        msg["Subject"] = f"📊 Attendance Report: {session_title}"
        
        # Email body (HTML)
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #0f172a;">📊 Attendance Report</h2>
                    <p><strong>Session:</strong> {session_title}</p>
                    <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Total Attendees:</strong> {len(attendance_data)}</p>
                    
                    <h3 style="color: #3b82f6;">Attendance Details</h3>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr style="background: #f3f4f6;">
                            <th style="padding: 10px; text-align: left; border: 1px solid #d1d5db;">Student ID</th>
                            <th style="padding: 10px; text-align: left; border: 1px solid #d1d5db;">Email</th>
                            <th style="padding: 10px; text-align: left; border: 1px solid #d1d5db;">Joined At</th>
                            <th style="padding: 10px; text-align: left; border: 1px solid #d1d5db;">Left At</th>
                            <th style="padding: 10px; text-align: left; border: 1px solid #d1d5db;">Duration</th>
                        </tr>
        """
        
        for item in attendance_data:
            body += f"""
                        <tr style="border: 1px solid #d1d5db;">
                            <td style="padding: 10px;">{item['id']}</td>
                            <td style="padding: 10px;">{item['email']}</td>
                            <td style="padding: 10px;">{item['joined_at']}</td>
                            <td style="padding: 10px;">{item['left_at']}</td>
                            <td style="padding: 10px;">{item.get('duration_min', '-')}</td>
                        </tr>
            """
        
        body += """
                    </table>
                    
                    <p style="color: #6b7280; font-size: 12px; margin-top: 30px;">
                        This is an automated email from Student Engagement System.
                    </p>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(body, "html"))
        
        # Attach CSV file
        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(csv_content.encode())
        encoders.encode_base64(attachment)
        attachment.add_header("Content-Disposition", f"attachment; filename=attendance_{session_title}.csv")
        msg.attach(attachment)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email sent to {teacher_email}")
        return True
        
    except Exception as e:
        print(f"❌ Email send failed: {e}")
        raise HTTPException(500, f"Failed to send email: {str(e)}")


# ==================== STUDENT JOIN ====================

@router.post("/join/{session_id}")
def mark_join(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✅ FIXED: Student joins a session.
    
    Behavior:
    1. First join: Create attendance record
    2. Rejoin (after leave): Update left_at=None
    3. Already present: Return status (no change)
    """
    if current_user.role != "student":
        raise HTTPException(403, "Only students can join sessions")

    # 1️⃣ Verify session exists and is active
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    if session.ended_at:
        raise HTTPException(403, "Session has ended")

    if session.is_locked:
        raise HTTPException(403, "Session is locked by teacher")

    # 2️⃣ Check if already joined
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.student_id == current_user.id
    ).first()

    # 3️⃣ Handle different states
    if attendance is None:
        # ✅ First join: Create new record
        attendance = Attendance(
            session_id=session_id,
            student_id=current_user.id,
            joined_at=datetime.utcnow()
        )
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
        
        print(f"✅ Student {current_user.id} joined session {session_id}")

        return {
            "status": "joined",
            "session_id": session_id,
            "student_id": current_user.id,
            "joined_at": attendance.joined_at.isoformat(),
            "message": "Successfully joined session"
        }

    elif attendance.left_at is not None:
        # ✅ Rejoin: Mark as present again
        attendance.left_at = None
        attendance.joined_at = datetime.utcnow()  # Reset join time
        db.commit()
        db.refresh(attendance)
        
        print(f"🔄 Student {current_user.id} rejoined session {session_id}")

        return {
            "status": "rejoined",
            "session_id": session_id,
            "student_id": current_user.id,
            "joined_at": attendance.joined_at.isoformat(),
            "message": "Successfully rejoined session"
        }

    else:
        # ✅ Already present: No change needed
        return {
            "status": "already_present",
            "session_id": session_id,
            "student_id": current_user.id,
            "joined_at": attendance.joined_at.isoformat(),
            "message": "Student is already present in session"
        }


# ==================== STUDENT LEAVE ====================

@router.post("/leave/{session_id}")
def mark_leave(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✅ FIXED: Student leaves a session.

    - Calculates attended duration
    - Accumulates total duration
    - Marks student as left
    """
    if current_user.role != "student":
        raise HTTPException(403, "Only students can leave sessions")

    # 1️⃣ Find attendance record
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.student_id == current_user.id
    ).first()

    if not attendance:
        return {
            "status": "not_joined",
            "session_id": session_id,
            "student_id": current_user.id,
            "message": "Student was not in this session"
        }

    # 2️⃣ Only update if student is currently present
    if attendance.left_at is None:
        now = datetime.utcnow()

        # ✅ CALCULATE DURATION
        session_seconds = int((now - attendance.joined_at).total_seconds())

        # ✅ ACCUMULATE TOTAL TIME
        attendance.total_duration_seconds += session_seconds

        # ✅ MARK AS LEFT
        attendance.left_at = now

        db.commit()
        db.refresh(attendance)

        print(
            f"👋 Student {current_user.id} left session {session_id} "
            f"(+{session_seconds}s, total={attendance.total_duration_seconds}s)"
        )

    return {
        "status": "left",
        "session_id": session_id,
        "student_id": current_user.id,
        "left_at": attendance.left_at.isoformat(),
        "total_duration_seconds": attendance.total_duration_seconds,
        "message": "Successfully left session"
    }


# ==================== ATTENDANCE COUNT (FIXED) ====================

@router.get("/count/{session_id}")
def get_attendance_count(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can view attendance")

    # 1️⃣ Get session
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    # 2️⃣ Calculate session duration (seconds)
    end_time = session.ended_at or datetime.utcnow()
    session_duration = (end_time - session.started_at).total_seconds()

    if session_duration <= 0:
        return {
            "session_id": session_id,
            "valid_attendance": 0,
            "currently_present": 0,
        }

    # 3️⃣ Get attendance records
    records = db.query(Attendance).filter(
        Attendance.session_id == session_id
    ).all()

    valid_attendance = 0
    currently_present = 0

    for a in records:
        # Base duration
        duration = 0

        # Case 1: Student already left
        if a.left_at:
            duration = (a.left_at - a.joined_at).total_seconds()
        else:
            # Case 2: Student still present
            duration = (datetime.utcnow() - a.joined_at).total_seconds()
            currently_present += 1

        # 4️⃣ Apply 15% rule
        percentage = (duration / session_duration) * 100

        if percentage >= 15:
            valid_attendance += 1

    print(f"\n📊 Correct Attendance Count for Session {session_id}")
    print(f"   Valid Attendance (≥15%): {valid_attendance}")
    print(f"   Currently Present: {currently_present}\n")

    return {
        "session_id": session_id,
        "valid_attendance": valid_attendance,
        "currently_present": currently_present,
    }

# ==================== VIEW PARTICIPANTS (DETAILED) ====================

@router.get("/session/{session_id}/participants")
def get_participants(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all participants in a session with details."""
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can view participants")

    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    # Join Attendance with User
    records = (
        db.query(Attendance, User)
        .join(User, Attendance.student_id == User.id)
        .filter(Attendance.session_id == session_id)
        .all()
    )

    participants = []

    for attendance, user in records:
        is_active = attendance.left_at is None
        
        duration_seconds = None
        if attendance.left_at:
            duration_seconds = int(
                (attendance.left_at - attendance.joined_at).total_seconds()
            )
        
        participants.append({
            "user_id": f"student-{user.id}",
            "email": user.email,
            "role": "audience",
            "status": "present" if is_active else "left",
            "joined_at": attendance.joined_at.isoformat(),
            "left_at": attendance.left_at.isoformat() if attendance.left_at else None,
            "duration_seconds": duration_seconds,
        })

    return {
        "session_id": session_id,
        "count": len(participants),
        "currently_present": sum(1 for p in participants if p["status"] == "present"),
        "participants": participants,
    }


# ==================== GET ATTENDEES (DETAILED LIST) ====================

@router.get("/session/{session_id}/students")
def get_attendees(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed attendee list."""
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can view attendees")

    records = (
        db.query(Attendance, User)
        .join(User, Attendance.student_id == User.id)
        .filter(Attendance.session_id == session_id)
        .order_by(Attendance.joined_at.asc())
        .all()
    )

    students = []
    for attendance, user in records:
        duration_seconds = None
        if attendance.left_at:
            duration_seconds = int(
                (attendance.left_at - attendance.joined_at).total_seconds()
            )

        students.append({
            "id": user.id,
            "email": user.email,
            "joined_at": attendance.joined_at.isoformat(),
            "left_at": attendance.left_at.isoformat() if attendance.left_at else None,
            "duration_seconds": duration_seconds,
            "is_present": attendance.left_at is None,
        })

    return {
        "session_id": session_id,
        "count": len(students),
        "currently_present": sum(1 for s in students if s["is_present"]),
        "students": students,
    }


# ==================== DOWNLOAD CSV ====================
@router.get("/session/{session_id}/download")
def download_attendance(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can download attendance")

    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session or not session.ended_at:
        raise HTTPException(400, "Session must be ended")

    records = (
        db.query(Attendance, User)
        .join(User, Attendance.student_id == User.id)
        .filter(Attendance.session_id == session_id)
        .order_by(Attendance.joined_at.asc())
        .all()
    )

    session_duration_sec = (
        session.ended_at - session.started_at
    ).total_seconds()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Student ID",
        "Email",
        "Joined At",
        "Left At",
        "Duration (minutes)",
        "Status"
    ])

    for attendance, user in records:
        end_time = attendance.left_at or session.ended_at
        duration_sec = (end_time - attendance.joined_at).total_seconds()
        duration_min = round(duration_sec / 60, 2)

        attendance_percentage = (duration_sec / session_duration_sec) * 100

        status = "Present" if attendance_percentage >= 15 else "Absent"

        writer.writerow([
            user.id,
            user.email,
            attendance.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            end_time.strftime("%Y-%m-%d %H:%M:%S"),
            duration_min,
            status,
        ])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=session_{session_id}_attendance.csv"
        }
    )


# ==================== SEND EMAIL ====================

@router.post("/session/{session_id}/send-email")
def send_attendance_email_endpoint(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send attendance report to teacher's email (15% rule applied)."""

    # ✅ STEP 0: Authorization
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can request attendance email")

    # ✅ STEP 1: Fetch session
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    if session.ended_at is None:
        raise HTTPException(400, "Session must be ended before sending report")

    # ✅ STEP 2: Calculate total session duration (ONCE)
    session_duration_sec = (
        session.ended_at - session.started_at
    ).total_seconds()

    if session_duration_sec <= 0:
        raise HTTPException(400, "Invalid session duration")

    # ✅ STEP 3: Fetch attendance records
    records = (
        db.query(Attendance, User)
        .join(User, Attendance.student_id == User.id)
        .filter(Attendance.session_id == session_id)
        .order_by(Attendance.joined_at.asc())
        .all()
    )

    if not records:
        raise HTTPException(400, "No attendance records for this session")

    # ✅ STEP 4: Build attendance data WITH 15% RULE
    attendance_data = []

    for attendance, user in records:
        # Use left_at OR session end time
        end_time = attendance.left_at or session.ended_at

        duration_sec = (end_time - attendance.joined_at).total_seconds()
        duration_min = round(duration_sec / 60, 2)

        attendance_percentage = (duration_sec / session_duration_sec) * 100

        status = "Present" if attendance_percentage >= 15 else "Absent"

        attendance_data.append({
            "id": user.id,
            "email": user.email,
            "joined_at": attendance.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            "left_at": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_min": duration_min,
            "status": status,
        })

    # ✅ STEP 5: Send email
    send_attendance_email(
        current_user.email,
        session.title,
        attendance_data
    )

    return {
        "status": "success",
        "message": f"Attendance report sent to {current_user.email}",
        "session_id": session_id,
        "attendees_count": len(attendance_data),
    }
