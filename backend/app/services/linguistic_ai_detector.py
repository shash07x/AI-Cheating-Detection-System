import re
import numpy as np
from collections import Counter

# Common AI phrases
AI_PATTERNS = [
    "firstly",
    "secondly",
    "in conclusion",
    "overall",
    "moreover",
    "furthermore",
    "additionally",
    "to summarize",
    "on the other hand"
]

def extract_features(text: str):
    words = text.lower().split()
    sentences = re.split(r"[.!?]", text)

    if len(words) == 0:
        return {}

    word_count = len(words)
    unique_words = len(set(words))

    avg_sentence_length = np.mean([
        len(s.split()) for s in sentences if len(s.split()) > 0
    ])

    filler_words = ["um", "uh", "like", "you know", "actually"]
    filler_count = sum(text.lower().count(f) for f in filler_words)

    ai_phrase_hits = sum(text.lower().count(p) for p in AI_PATTERNS)

    vocab_richness = unique_words / max(word_count, 1)

    return {
        "avg_sentence_length": avg_sentence_length,
        "filler_ratio": filler_count / max(word_count, 1),
        "ai_phrase_hits": ai_phrase_hits,
        "vocab_richness": vocab_richness
    }


def detect_ai_text(transcript: str):
    """
    Returns:
      ai_percent (0–100)
      human_percent (0–100)
    """

    if not transcript or len(transcript) < 20:
        return 0, 100

    f = extract_features(transcript)

    score = 0

    # Long structured sentences → AI
    if f["avg_sentence_length"] > 18:
        score += 25

    # Very rich vocabulary → AI
    if f["vocab_richness"] > 0.7:
        score += 20

    # No fillers → AI
    if f["filler_ratio"] < 0.002:
        score += 20

    # Explicit AI phrases
    score += min(f["ai_phrase_hits"] * 10, 25)

    ai_percent = min(score, 100)
    human_percent = 100 - ai_percent

    return ai_percent, human_percent