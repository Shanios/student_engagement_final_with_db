import os
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import numpy as np

NOTES_FOLDER = "../notes"
CHUNK_SIZE = 2500  # correct chunk size

model = SentenceTransformer("all-MiniLM-L6-v2")

def pdf_to_text(path):
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def clean_text(text):
    # Remove duplicates + fix broken newlines
    cleaned_lines = []
    for line in text.split("\n"):
        line = line.strip()
        if line and line not in cleaned_lines:
            cleaned_lines.append(line)

    # Join and fix spacing
    text = " ".join(cleaned_lines)
    text = text.replace("  ", " ")
    return text

def chunk_text(text, chunk_size=1500):
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size].strip()
        if len(chunk) > 80:
            chunks.append(chunk)
    return chunks

def build_kb():
    all_chunks = []

    for file in os.listdir(NOTES_FOLDER):
        if file.endswith(".pdf"):
            print(f"Processing: {file}")

            raw_text = pdf_to_text(os.path.join(NOTES_FOLDER, file))
            cleaned = clean_text(raw_text)
            chunks = chunk_text(cleaned, CHUNK_SIZE)

            all_chunks.extend(chunks)

    print(f"Total text chunks: {len(all_chunks)}")

    embeddings = model.encode(all_chunks, convert_to_numpy=True)

    np.save("embeddings.npy", embeddings)
    np.save("text_chunks.npy", np.array(all_chunks, dtype=object))

    print("Knowledge base built successfully!")

if __name__ == "__main__":
    build_kb()
