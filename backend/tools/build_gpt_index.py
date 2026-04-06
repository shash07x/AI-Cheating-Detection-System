from datasets import load_dataset
from sentence_transformers import SentenceTransformer
import faiss, numpy as np, pickle

model = SentenceTransformer("all-MiniLM-L6-v2")

dataset = load_dataset("Anthropic/hh-rlhf", split="train[:5000]")

texts = [x["chosen"] for x in dataset]

embeddings = model.encode(texts, show_progress_bar=True)

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(np.array(embeddings))

faiss.write_index(index, "gpt_index.faiss")

with open("gpt_texts.pkl","wb") as f:
    pickle.dump(texts,f)