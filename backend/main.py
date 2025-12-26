from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from question_papers import router as qpapers_router
from database import Base, engine
from rag.rag_chatbot_lm import answer_question
from auth import router as auth_router, get_current_user
from notes import router as notes_router
from engagement import router as engagement_router
from rag_api import router as rag_api_router
from models import User, EngagementSession, EngagementPoint
from models import Base
from threading import Thread
import time
from datetime import datetime, timedelta
from database import SessionLocal
from slowapi import Limiter
from slowapi.util import get_remote_address
from dotenv import load_dotenv
import os 
from video_sessions import router as video_router
from attendance import router as attendance_router

# ✅ NEW: Import analytics modules
from analytics import get_comprehensive_analytics, generate_summary_report
from reports import create_report_package, export_to_whatsapp_format

load_dotenv()  # Load from .env file
Base.metadata.create_all(bind=engine)
app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# ---- CORS (frontend dev: Vite on 5173) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====== DATABASE DEPENDENCY ======
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ====== CHATBOT ======

class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


@app.get("/")
def home():
    return {"message": "Backend is running"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    ans = answer_question(payload.question)
    return ChatResponse(answer=ans)


# ====== SESSION WATCHDOG (AUTO-END INACTIVE SESSIONS) ======
def session_watchdog():
    """
    Background thread that auto-ends sessions that haven't had heartbeats.
    Prevents sessions from staying open indefinitely.
    """
    while True:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            timeout = timedelta(seconds=30)

            sessions = db.query(EngagementSession).filter(
                EngagementSession.ended_at.is_(None)
            ).all()

            for s in sessions:
                if s.last_seen_at and now - s.last_seen_at > timeout:
                    s.ended_at = now
                    print(f"🔒 Auto-ended inactive session {s.id}")

            db.commit()
        except Exception as e:
            print(f"❌ Watchdog error: {e}")
        finally:
            db.close()

        time.sleep(10)


Thread(target=session_watchdog, daemon=True).start()


# ====== ✅ NEW: BACKGROUND JOB FOR REPORT GENERATION ======
def generate_session_report(session_id: int):
    """
    Background job: Generate analytics + reports for a completed session.
    
    This runs asynchronously after the teacher ends the session.
    No UI blocking.
    
    Flow:
    1. Fetch engagement points from DB
    2. Run analytics computation
    3. Generate graphs (PNG base64)
    4. Create report package
    5. TODO: Send WhatsApp message
    
    Args:
        session_id: The ID of the session to generate report for
    """
    db = SessionLocal()
    try:
        print(f"📊 Starting report generation for session {session_id}")
        
        # Fetch session
        session = db.query(EngagementSession).filter(
            EngagementSession.id == session_id
        ).first()
        
        if not session:
            print(f"❌ Session {session_id} not found")
            return
        
        if not session.ended_at:
            print(f"⚠️ Session {session_id} is still active, skipping report")
            return
        
        # Fetch all engagement points
        points = db.query(EngagementPoint).filter(
            EngagementPoint.session_id == session_id
        ).order_by(EngagementPoint.timestamp.asc()).all()
        
        if not points:
            print(f"⚠️ No engagement data for session {session_id}")
            return
        
        # Convert to dict format for analytics
        points_data = [
            {
                'timestamp': p.timestamp.isoformat(), 
                'score': p.score
            }
            for p in points
        ]
        
        print(f"📈 Computing analytics from {len(points_data)} points")
        
        # ✅ Run analytics engine (uses BOTH old and new analytics)
        analytics = get_comprehensive_analytics(points_data)
        
        # ✅ Generate reports and graphs
        report_package = create_report_package(analytics)
        whatsapp_format = export_to_whatsapp_format(report_package)
        
        # Print summary
        print(f"✅ Report generated successfully!")
        print(f"   Average engagement: {analytics['summary']['avg_score']:.1%}")
        print(f"   Peak engagement: {analytics['summary']['max_score']:.1%}")
        print(f"   Total points: {analytics['summary']['total_points']}")
        print(f"   Duration: {analytics['summary']['duration_formatted']}")
        
        # ===== TODO: SEND WHATSAPP MESSAGE =====
        # whatsapp_client.send_engagement_report(
        #     session.teacher_id,
        #     whatsapp_format
        # )
        print(f"📱 TODO: Send WhatsApp message to teacher")
        print(f"\nReport Package Keys: {list(whatsapp_format.keys())}")
        
    except Exception as e:
        print(f"❌ Report generation error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# ====== ✅ NEW: ENDPOINT TO TRIGGER REPORT GENERATION ======
@app.post("/api/engagement/sessions/{session_id}/generate-report")
async def trigger_report(
    session_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Manually trigger report generation for a completed session.
    
    Only the session teacher can request this.
    
    This endpoint:
    1. Validates the session exists and is owned by the teacher
    2. Validates the session has ended
    3. Adds a background task to generate the report
    4. Returns immediately (non-blocking)
    
    Args:
        session_id: The engagement session ID
        background_tasks: FastAPI background tasks
        current_user: The authenticated teacher
        db: Database session
    
    Returns:
        JSON with status and message
    """
    
    # Validate teacher owns this session
    session = db.query(EngagementSession).filter(
        EngagementSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )
    
    if session.teacher_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the session teacher can request reports"
        )
    
    # Validate session is ended
    if session.ended_at is None:
        raise HTTPException(
            status_code=400,
            detail="Session must be ended before generating report"
        )
    
    # ✅ Add background task (non-blocking)
    background_tasks.add_task(generate_session_report, session_id)
    
    print(f"📋 Report generation queued for session {session_id}")
    
    return {
        "status": "report_generation_queued",
        "session_id": session_id,
        "message": "Report will be generated asynchronously and delivered via WhatsApp"
    }


# ====== ROUTER REGISTRATION ======
app.include_router(qpapers_router)
app.include_router(auth_router)          # /api/auth/...
app.include_router(notes_router)         # /api/notes/...
app.include_router(engagement_router)    # /api/engagement/...
app.include_router(video_router)         # /api/video/...
app.include_router(rag_api_router)       # /api/rag/...
app.include_router(attendance_router)    # /api/attendance/...


# ✅ NOTE: Analytics router will be added separately as analytics_router.py
# For now, the endpoints are handled in main.py above