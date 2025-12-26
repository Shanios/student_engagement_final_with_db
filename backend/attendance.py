from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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

# ✅ Load environment variables
load_dotenv()

# ==================== EMAIL CONFIGURATION ====================
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# Validate credentials
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
    """Student joins a session."""
    if current_user.role != "student":
        raise HTTPException(403, "Only students can join sessions")

    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    if session.ended_at:
        raise HTTPException(403, "Session has ended")

    if session.is_locked:
        raise HTTPException(403, "Session is locked by teacher")

    try:
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
        }

    except IntegrityError:
        db.rollback()
        existing = db.query(Attendance).filter(
            Attendance.session_id == session_id,
            Attendance.student_id == current_user.id
        ).first()

        return {
            "status": "already_joined",
            "session_id": session_id,
            "student_id": current_user.id,
            "joined_at": existing.joined_at.isoformat() if existing else None,
        }

    except Exception as err:
        db.rollback()
        print(f"❌ Join error: {err}")
        raise HTTPException(500, "Failed to record attendance")


# ==================== STUDENT LEAVE ====================

@router.post("/leave/{session_id}")
def mark_leave(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Student leaves a session."""
    if current_user.role != "student":
        raise HTTPException(403, "Only students can leave sessions")

    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.student_id == current_user.id
    ).first()

    if not attendance:
        return {
            "status": "not_joined",
            "session_id": session_id,
            "student_id": current_user.id,
        }

    if not attendance.left_at:
        attendance.left_at = datetime.utcnow()
        db.commit()

        print(f"👋 Student {current_user.id} left session {session_id}")

    return {
        "status": "left",
        "session_id": session_id,
        "student_id": current_user.id,
        "left_at": attendance.left_at.isoformat(),
    }


# ==================== VIEW PARTICIPANTS ====================

@router.get("/session/{session_id}/participants")
def get_participants(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all participants in a session."""
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can view participants")

    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    records = (
        db.query(Attendance, User)
        .join(User, Attendance.student_id == User.id)
        .filter(Attendance.session_id == session_id)
        .all()
    )

    participants = []

    for attendance, user in records:
        is_active = attendance.left_at is None
        
        participants.append({
            "user_id": f"student-{user.id}",
            "role": "audience",
            "status": "joined" if is_active else "left",
            "joined_at": attendance.joined_at.isoformat(),
            "left_at": attendance.left_at.isoformat() if attendance.left_at else None,
            "duration_seconds": int(
                (attendance.left_at - attendance.joined_at).total_seconds()
            ) if attendance.left_at else None,
        })

    return {
        "session_id": session_id,
        "count": len(participants),
        "participants": participants,
    }


# ==================== ATTENDANCE COUNT ====================

@router.get("/count/{session_id}")
def get_attendance_count(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get live attendance count."""
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can view attendance")

    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    total_joined = db.query(Attendance).filter(
        Attendance.session_id == session_id
    ).count()

    currently_present = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.left_at.is_(None)
    ).count()

    return {
        "session_id": session_id,
        "total_joined": total_joined,
        "currently_present": currently_present,
    }


# ==================== GET ATTENDEES ====================

@router.get("/session/{session_id}/students")
def get_attendees(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed attendee list."""
    if current_user.role != "teacher":
        raise HTTPException(403)

    records = (
        db.query(Attendance, User)
        .join(User, Attendance.student_id == User.id)
        .filter(Attendance.session_id == session_id)
        .all()
    )

    students = []
    for attendance, user in records:
        duration = None
        if attendance.left_at:
            duration = int(
                (attendance.left_at - attendance.joined_at).total_seconds()
            )

        students.append({
            "id": user.id,
            "email": user.email,
            "joined_at": attendance.joined_at.isoformat(),
            "left_at": attendance.left_at.isoformat() if attendance.left_at else None,
            "duration_seconds": duration,
            "is_present": attendance.left_at is None,
        })

    return {
        "session_id": session_id,
        "count": len(students),
        "students": students,
    }


# ==================== DOWNLOAD CSV ====================

@router.get("/session/{session_id}/download")
def download_attendance(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download attendance as CSV."""
    if current_user.role != "teacher":
        raise HTTPException(403)

    records = (
        db.query(Attendance, User)
        .join(User, Attendance.student_id == User.id)
        .filter(Attendance.session_id == session_id)
        .order_by(Attendance.joined_at.asc())
        .all()
    )

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
        duration_min = None
        status = "Present"

        if attendance.left_at:
            duration_sec = (attendance.left_at - attendance.joined_at).total_seconds()
            duration_min = round(duration_sec / 60, 2)
            status = "Left"

        writer.writerow([
            user.id,
            user.email,
            attendance.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            attendance.left_at.strftime("%Y-%m-%d %H:%M:%S") if attendance.left_at else "-",
            duration_min if duration_min else "-",
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
    """Send attendance report to teacher's email."""
    
    if current_user.role != "teacher":
        raise HTTPException(403, "Only teacher can request attendance email")
    
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(404, "Session not found")
    
    records = (
        db.query(Attendance, User)
        .join(User, Attendance.student_id == User.id)
        .filter(Attendance.session_id == session_id)
        .order_by(Attendance.joined_at.asc())
        .all()
    )
    
    if not records:
        raise HTTPException(400, "No attendance records for this session")
    
    # Format attendance data
    attendance_data = []
    for attendance, user in records:
        duration_min = None
        status = "Present"
        
        if attendance.left_at:
            duration_sec = (attendance.left_at - attendance.joined_at).total_seconds()
            duration_min = round(duration_sec / 60, 2)
            status = "Left"
        
        attendance_data.append({
            "id": user.id,
            "email": user.email,
            "joined_at": attendance.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            "left_at": attendance.left_at.strftime("%Y-%m-%d %H:%M:%S") if attendance.left_at else "-",
            "duration_min": duration_min,
            "status": status,
        })
    
    # Send email
    send_attendance_email(current_user.email, session.title, attendance_data)
    
    return {
        "status": "success",
        "message": f"Attendance report sent to {current_user.email}",
        "session_id": session_id,
        "attendees_count": len(attendance_data),
    }