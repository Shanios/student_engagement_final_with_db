import os
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Note, User
from auth import get_current_user   # <-- use the helper we wrote

router = APIRouter(prefix="/api/notes", tags=["notes"])


# === DB dependency ===
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# === Pydantic schema ===
class NoteOut(BaseModel):
    id: int
    title: str
    subject: str | None = None
    uploaded_at: datetime
    owner_id: int | None = None

    class Config:
        orm_mode = True


BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=NoteOut)
async def upload_note(
    title: str = Form(...),
    subject: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <-- JWT user here
):
    # 🔒 only teachers can upload
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can upload notes")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    safe_name = f"{uuid.uuid4().hex}.pdf"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    note = Note(
        title=title,
        subject=subject,
        filename=safe_name,
        owner_id=current_user.id,   # link to teacher
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/", response_model=list[NoteOut])
def list_notes(subject: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Note)
    if subject:
        q = q.filter(Note.subject == subject)
    return q.order_by(Note.uploaded_at.desc()).all()


@router.get("/{note_id}/download")
def download_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    file_path = os.path.join(UPLOAD_DIR, note.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing on server")

    download_name = f"{note.title}.pdf"
    return FileResponse(file_path, filename=download_name, media_type="application/pdf")
