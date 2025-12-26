# backend/rag_api.py
from fastapi import APIRouter, HTTPException
from rag.build_knowledge import build_kb  # make sure function name matches your file

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/rebuild")
def rebuild_kb():
    """
    Rebuild embeddings from current PDFs.
    Call this manually after uploading many new notes.
    """
    try:
        build_kb()
        return {"status": "ok", "message": "Knowledge base rebuilt"}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
