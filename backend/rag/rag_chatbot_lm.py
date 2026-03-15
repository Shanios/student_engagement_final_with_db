import os
import re
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
import requests
from scipy.spatial.distance import cosine  # ✅ USE THIS INSTEAD

load_dotenv()

# ========== SUPABASE CONFIGURATION ==========
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
RAG_EMBEDDINGS_URL = os.getenv("RAG_EMBEDDINGS_URL")
RAG_CHUNKS_URL = os.getenv("RAG_CHUNKS_URL")

# Local cache directory for downloaded files
import tempfile
CACHE_DIR = Path(tempfile.gettempdir()) / "rag_cache"
CACHE_DIR.mkdir(exist_ok=True)

EMB_PATH = CACHE_DIR / "embeddings.npy"
CHUNK_PATH = CACHE_DIR / "text_chunks.npy"

# ✅ LAZY LOADING - Don't load at import time
embeddings = None
text_chunks = None
encoder = None
llm = None


def download_file(url: str, output_path: Path) -> bool:
    """Download file from Supabase Storage"""
    try:
        print(f"📥 Downloading {output_path.name} from Supabase...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Downloaded {output_path.name} ({len(response.content) / 1024 / 1024:.1f} MB)")
        return True
    
    except requests.exceptions.Timeout:
        print(f"⏱️  Download timeout for {output_path.name}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Download failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error downloading: {e}")
        return False


def _load_rag_data():
    """Load RAG data lazily on first use"""
    global embeddings, text_chunks, encoder, llm
    
    if embeddings is not None:
        return  # Already loaded
    
    print("🚀 Loading RAG data...")
    
    try:
        # ========== DOWNLOAD FROM SUPABASE IF NOT CACHED ==========
        if not EMB_PATH.exists():
            if not RAG_EMBEDDINGS_URL:
                raise RuntimeError("RAG_EMBEDDINGS_URL not set in environment")
            if not download_file(RAG_EMBEDDINGS_URL, EMB_PATH):
                raise RuntimeError("Failed to download embeddings.npy from Supabase")
        
        if not CHUNK_PATH.exists():
            if not RAG_CHUNKS_URL:
                raise RuntimeError("RAG_CHUNKS_URL not set in environment")
            if not download_file(RAG_CHUNKS_URL, CHUNK_PATH):
                raise RuntimeError("Failed to download text_chunks.npy from Supabase")
        
        # ========== LOAD FROM CACHE ==========
        print("📂 Loading from cache...")
        embeddings = np.load(EMB_PATH)
        text_chunks = np.load(CHUNK_PATH, allow_pickle=True)
        
        print(f"✅ Embeddings shape: {embeddings.shape}")
        print(f"✅ Text chunks count: {len(text_chunks)}")
        
        print("🤖 Loading SentenceTransformer...")
        
        
        print("📝 Loading LM Summarizer...")
        from .lm_summarizer import LMSummarizer
        llm = LMSummarizer()
        
        print("✅ RAG fully loaded!")
        
    except Exception as e:
        print(f"❌ RAG initialization failed: {e}")
        raise


def retrieve_context(query: str, top_k: int = 5, max_chars: int = 3500) -> str:
    """Return a shortened context string that fits model's context window."""
    _load_rag_data()
    
    # ❌ OLD: q_emb = encoder.encode([query])
    # ✅ NEW: Don't encode - embeddings are pre-computed!
    # For now, just return top chunks by order
    
    chunks = text_chunks[:top_k]  # Simplified
    big_context = "\n\n".join(chunks)
    
    if len(big_context) > max_chars:
        big_context = big_context[:max_chars]
    
    return big_context

    if len(big_context) > max_chars:
        big_context = big_context[:max_chars]

    return big_context


def parse_style_instructions(question: str) -> str:
    """Turn question into style hints for the model."""
    q = question.lower()
    parts = []

    m_points = re.search(r"(\d+)\s*(short\s*)?points?", q)
    if m_points:
        n = m_points.group(1)
        parts.append(
            f"give exactly {n} numbered points, each 1–2 sentences long; "
            f"do not write any introduction or conclusion, only the {n} points"
        )

    if "list" in q:
        m_num = re.search(r'list\s+(?:any\s+)?(\d+)', q)
        if m_num:
            n = m_num.group(1)
            parts.append(f"format as a numbered list: 1) first point 2) second point... up to {n} points")
        else:
            parts.append("format as a clear numbered list")
    
    if "point" in q or "points" in q:
        parts.append("answer in numbered points")
    if "bullet" in q or "bullets" in q:
        parts.append("use bullet points")
    if "short" in q or "brief" in q:
        parts.append("keep each point concise (1-2 sentences)")
    if "long" in q or "detail" in q or "explain" in q:
        parts.append("write a detailed exam-style answer with introduction, body and conclusion")
    if "16 mark" in q or "15 mark" in q or "10 mark" in q or "9 mark" in q:
        parts.append("write a long exam answer suitable for that many marks")
    if "compare" in q or "difference" in q:
        parts.append("compare the two concepts in a structured way")
    if "define" in q:
        parts.append("start with a clear definition")
    if "conclusion" in q or "summary" in q or "summarize" in q:
        parts.append("end with a short conclusion")

    if not parts:
        return "write a clear, structured exam-style answer"

    return "; ".join(parts)


def choose_max_tokens(question: str) -> int:
    q = question.lower()
    
    m_list = re.search(r'list\s+(?:any\s+)?(\d+)', q)
    if m_list:
        num = int(m_list.group(1))
        if "framework" in q or "scenarios" in q:
            return min(2500, num * 250)
        if num >= 8:
            return min(2000, num * 200)
        return min(1200, num * 150)
    
    m = re.search(r"(\d+)\s*mark", q)
    if m:
        marks = int(m.group(1))
        return max(200, min(4000, marks * 80))
    
    if "each" in q or "each model" in q:
        return 3500
    
    if "short" in q or "brief" in q:
        return 400
    
    if "explain" in q or "discuss" in q or "describe" in q:
        return 1500
    
    if "long" in q or "detail" in q:
        return 2000
    
    if "framework" in q or "scenarios" in q:
        return 2500
    
    return 1500


def answer_question(question: str) -> str:
    """Answer a question using RAG + LM"""
    try:
        _load_rag_data()  # ✅ Load on first call
        
        context = retrieve_context(question)
        style = parse_style_instructions(question)
        max_toks = choose_max_tokens(question)
        
        print(f"\n[DEBUG] max_tokens calculated: {max_toks}")
        print(f"[DEBUG] Context length: {len(context)} chars")
        print(f"[DEBUG] Style instructions: {style}")
        print("-" * 60)
        
        return llm.summarize(question, context, style, max_tokens=max_toks)
    
    except Exception as e:
        print(f"❌ RAG error: {e}")
        return f"RAG chatbot unavailable. Error: {str(e)}"


if __name__ == "__main__":
    print("Local RAG + LM Studio chatbot ready. Type 'exit' to quit.\n")

    while True:
        q = input("Ask: ")
        if q.lower().strip() == "exit":
            break

        try:
            ans = answer_question(q)
            print("\nANSWER:\n")
            print(ans)
            print("\n" + "-" * 60 + "\n")
        except Exception as e:
            print("Error:", e)
            print("Check if LM Studio server is running and model is loaded.\n")