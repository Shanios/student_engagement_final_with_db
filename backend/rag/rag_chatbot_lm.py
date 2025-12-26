import os
import re
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from .lm_summarizer import LMSummarizer   # note the dot

BASE_DIR = os.path.dirname(__file__)      # folder: backend/rag
EMB_PATH = os.path.join(BASE_DIR, "embeddings.npy")
CHUNK_PATH = os.path.join(BASE_DIR, "text_chunks.npy")

# Load RAG data
embeddings = np.load(EMB_PATH)
text_chunks = np.load(CHUNK_PATH, allow_pickle=True)

# Encoder for similarity search
encoder = SentenceTransformer("all-MiniLM-L6-v2")

# Local LM Studio client
llm = LMSummarizer()


def retrieve_context(query: str, top_k: int = 5, max_chars: int = 3500) -> str:
    """Return a shortened context string that fits model's context window."""
    q_emb = encoder.encode([query])
    sims = cosine_similarity(q_emb, embeddings)[0]
    top_idx = sims.argsort()[-top_k:][::-1]
    chunks = [text_chunks[i] for i in top_idx]

    big_context = "\n\n".join(chunks)

    # Hard cap on length to avoid 4096-token overflow
    if len(big_context) > max_chars:
        big_context = big_context[:max_chars]

    return big_context


def parse_style_instructions(question: str) -> str:
    """Turn question into style hints for the model."""
    q = question.lower()
    parts = []

    # NEW: detect "N points" pattern
    m_points = re.search(r"(\d+)\s*(short\s*)?points?", q)
    if m_points:
        n = m_points.group(1)
        parts.append(
            f"give exactly {n} numbered points, each 1–2 sentences long; "
            f"do not write any introduction or conclusion, only the {n} points"
        )

    # UPDATED: Better detection for list-type questions
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
    
    # Check for "list N points/advantages/etc"
    m_list = re.search(r'list\s+(?:any\s+)?(\d+)', q)
    if m_list:
        num = int(m_list.group(1))
        if "framework" in q or "scenarios" in q:
            return min(2500, num * 250)  # ← Even more for framework questions
        # If asking for 8+ items with examples/explanations
        # If asking for 8+ items with examples/explanations, give more tokens
        if num >= 8:
            return min(2000, num * 200)  # ← Increased multiplier
        return min(1200, num * 150)
    
    m = re.search(r"(\d+)\s*mark", q)
    if m:
        marks = int(m.group(1))
        return max(200, min(4000, marks * 80))
    
    # Multi-part questions
    if "each" in q or "each model" in q:
        return 3500
    
    if "short" in q or "brief" in q:
        return 400
    
    if "explain" in q or "discuss" in q or "describe" in q:
        return 1500
    
    if "long" in q or "detail" in q:
        return 2000
    
    # Multi-factor with decision framework
    if "framework" in q or "scenarios" in q:
        return 2500  # ← NEW: for complex framework questions
    
    return 1500


def answer_question(question: str) -> str:
    context = retrieve_context(question)
    style = parse_style_instructions(question)
    max_toks = choose_max_tokens(question)
    
    # DEBUG PRINTS - Add these lines
    print(f"\n[DEBUG] max_tokens calculated: {max_toks}")
    print(f"[DEBUG] Context length: {len(context)} chars")
    print(f"[DEBUG] Style instructions: {style}")
    print("-" * 60)
    
    return llm.summarize(question, context, style, max_tokens=max_toks)


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