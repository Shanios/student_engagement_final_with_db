import os
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import SessionLocal
from models import Note, User
from auth import get_current_user

load_dotenv()

router = APIRouter(prefix="/api/notes", tags=["notes"])

# Local upload directory (temporary)
BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

print(f"📁 Notes upload directory: {UPLOAD_DIR}")

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
        from_attributes = True


@router.post("/upload", response_model=NoteOut)
async def upload_note(
    title: str = Form(...),
    subject: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload note (local storage - temporary)"""
    
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can upload notes")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    safe_name = f"{uuid.uuid4().hex}.pdf"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    # Save locally
    with open(file_path, "wb") as f:
        f.write(content)

    note = Note(
        title=title,
        subject=subject,
        filename=safe_name,
        owner_id=current_user.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    
    print(f"✅ Note uploaded locally: {safe_name}")
    return note


@router.get("/", response_model=list[NoteOut])
def list_notes(subject: str | None = None, db: Session = Depends(get_db)):
    """List all notes"""
    q = db.query(Note)
    if subject:
        q = q.filter(Note.subject == subject)
    return q.order_by(Note.uploaded_at.desc()).all()


@router.get("/{note_id}/download")
def download_note(note_id: int, db: Session = Depends(get_db)):
    """Download note from local storage"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    file_path = os.path.join(UPLOAD_DIR, note.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, filename=f"{note.title}.pdf")


@router.delete("/{note_id}")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete note"""
    
    note = db.query(Note).filter(Note.id == note_id).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if note.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only owner can delete")
    
    # Delete file
    file_path = os.path.join(UPLOAD_DIR, note.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from DB
    db.delete(note)
    db.commit()
    
    print(f"✅ Note deleted: {note_id}")
    return {"status": "deleted", "id": note_id}