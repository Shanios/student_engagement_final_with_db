import numpy as np
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from summarizer import Summarizer

EMB_PATH = "embeddings.npy"
CHUNK_PATH = "text_chunks.npy"

model = SentenceTransformer("all-MiniLM-L6-v2")
summarizer = Summarizer()

embeddings = np.load(EMB_PATH)
text_chunks = np.load(CHUNK_PATH, allow_pickle=True)

# Retrieve top paragraphs
def retrieve_text(query, top_k=13):
    query_emb = model.encode([query])
    sims = cosine_similarity(query_emb, embeddings)[0]
    top_idx = sims.argsort()[-top_k:][::-1]
    return "\n\n".join(text_chunks[i] for i in top_idx)


# 🔥 SMART STYLE INSTRUCTION PARSER
def parse_style_instructions(question: str) -> str:
    q = question.lower()

    instructions = ""

    # Point-wise
    if "point" in q or "points" in q:
        instructions += "Write the answer point-wise. "

    # Bullet format
    if "bullet" in q or "bullets" in q:
        instructions += "Use bullet points. "

    # Exam-style
    if "exam" in q:
        instructions += "Write in exam style with introduction, body, and conclusion. "

    # Define
    if "define" in q:
        instructions += "Start with a clear definition. "

    # Explain
    if "explain" in q:
        instructions += "Give a clear explanation with examples if needed. "

    # List
    if "list" in q:
        instructions += "List the key points clearly. "

    # Compare
    if "compare" in q or "difference" in q:
        instructions += "Provide a comparison table-style explanation. "

    # Title
    if "title" in q or "heading" in q:
        instructions += "Add a suitable title to the answer. "

    # Conclusion
    if "conclusion" in q or "summarize" in q:
        instructions += "End with a short conclusion. "

    # If no style detected, use default general answer
    if instructions.strip() == "":
        instructions = "Write a clear and structured answer."

    return instructions


# 🔥 DYNAMIC ANSWER LENGTH LOGIC
def choose_max_len(question: str) -> int:
    q = question.lower()

    match = re.search(r"(\d+)\s*mark", q)
    if match:
        marks = int(match.group(1))
        return max(80, min(400, marks * 22))

    if "short" in q or "brief" in q:
        return 80

    if "long" in q or "detail" in q or "expand" in q:
        return 300

    return 160  # default


def answer_question(question: str) -> str:
    context = retrieve_text(question)
    max_len = choose_max_len(question)
    style = parse_style_instructions(question)

    answer = summarizer.summarize(
        question=question,
        context=context,
        style_instructions=style,
        max_len=max_len
    )
    return answer


print("🔥 Smart Exam RAG Chatbot Ready. Type 'exit' to stop.")

while True:
    q = input("\nAsk: ")

    if q.lower() == "exit":
        break

    response = answer_question(q)
    print("\nANSWER:\n", response)
