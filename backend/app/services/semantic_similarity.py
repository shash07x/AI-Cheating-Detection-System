from pathlib import Path
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

# Go to backend directory safely
BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
INDEX_PATH = BASE_DIR / "gpt_index.faiss"

print("✅ Loading FAISS index from:", INDEX_PATH)

index = faiss.read_index(str(INDEX_PATH))


def compute_similarity(text):

    emb = model.encode([text])
    D, _ = index.search(np.array(emb), 5)

    score = 100 - float(D.mean())
    return max(0, min(100, score))