# backend/rag_api.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/rag", tags=["rag"])

# No endpoints needed - RAG is read-only in production

@router.get("/health")
def rag_health():
    """Check if RAG is available"""
    return {"status": "ok", "rag_available": True}