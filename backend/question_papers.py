# backend/question_papers.py

import os
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import SessionLocal
from models import QuestionPaper, User
from auth import get_current_user

load_dotenv()

# THIS is what main.py imports
router = APIRouter(prefix="/api/qpapers", tags=["question_papers"])

# Local upload directory (temporary)
BASE_DIR = os.path.dirname(__file__)
QP_UPLOAD_DIR = os.path.join(BASE_DIR, "qp_uploads")
os.makedirs(QP_UPLOAD_DIR, exist_ok=True)

print(f"📁 Question papers upload directory: {QP_UPLOAD_DIR}")

# ---------- DB dependency ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Pydantic schema ----------
class QuestionPaperOut(BaseModel):
    id: int
    title: str
    subject: str | None = None
    exam_type: str | None = None
    year: int | None = None
    uploaded_at: datetime
    owner_id: int | None = None

    class Config:
        orm_mode = True
        from_attributes = True


# ---------- Upload (TEACHER ONLY) ----------
@router.post("/upload", response_model=QuestionPaperOut)
async def upload_qpaper(
    request: Request,
    title: str = Form(...),
    subject: str = Form(...),
    year: int = Form(...),
    exam_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Debug: see exactly what frontend sends
    print(await request.form())

    # Only teacher can upload
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can upload question papers")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Check file size (max 50MB)
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    safe_name = f"{uuid.uuid4().hex}.pdf"
    file_path = os.path.join(QP_UPLOAD_DIR, safe_name)

    # Save locally
    with open(file_path, "wb") as f:
        f.write(content)

    qp = QuestionPaper(
        title=title,
        subject=subject,
        exam_type=exam_type,
        year=year,
        filename=safe_name,
        owner_id=current_user.id,
    )
    db.add(qp)
    db.commit()
    db.refresh(qp)
    
    print(f"✅ Question paper uploaded locally: {safe_name}")
    return qp


# ---------- List with filters ----------
@router.get("/", response_model=list[QuestionPaperOut])
def list_qpapers(
    subject: str | None = None,
    year: int | None = None,
    exam_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # must be logged in
):
    q = db.query(QuestionPaper)

    if subject:
        q = q.filter(QuestionPaper.subject == subject)
    if year:
        q = q.filter(QuestionPaper.year == year)
    if exam_type:
        q = q.filter(QuestionPaper.exam_type == exam_type)

    return q.order_by(QuestionPaper.uploaded_at.desc()).all()


# ---------- Download ----------
@router.get("/{qp_id}/download")
def download_qpaper(
    qp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # must be logged in
):
    qp = db.query(QuestionPaper).filter(QuestionPaper.id == qp_id).first()
    if not qp:
        raise HTTPException(status_code=404, detail="Question paper not found")

    file_path = os.path.join(QP_UPLOAD_DIR, qp.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    download_name = f"{qp.title}.pdf"
    return FileResponse(file_path, filename=download_name, media_type="application/pdf")


# ---------- Delete ----------
@router.delete("/{qp_id}")
def delete_qpaper(
    qp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete question paper"""
    
    qp = db.query(QuestionPaper).filter(QuestionPaper.id == qp_id).first()
    
    if not qp:
        raise HTTPException(status_code=404, detail="Question paper not found")
    
    # Only owner can delete
    if qp.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only owner can delete")
    
    # Delete file
    file_path = os.path.join(QP_UPLOAD_DIR, qp.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from DB
    db.delete(qp)
    db.commit()
    
    print(f"✅ Question paper deleted: {qp_id}")
    return {"status": "deleted", "id": qp_id}