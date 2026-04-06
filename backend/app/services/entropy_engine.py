import re
import numpy as np

FILLER_WORDS = [
    "um", "uh", "like", "you know",
    "basically", "actually", "so",
    "well", "right"
]

def lexical_diversity(text):
    words = re.findall(r"\w+", text.lower())
    if not words:
        return 0
    return len(set(words)) / len(words)


def filler_density(text):
    text_lower = text.lower()
    count = sum(text_lower.count(word) for word in FILLER_WORDS)
    total_words = len(text_lower.split())
    if total_words == 0:
        return 0
    return count / total_words


def structural_score(text):
    sentences = re.split(r"[.!?]", text)
    sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
    if not sentence_lengths:
        return 0
    variance = np.var(sentence_lengths)
    return 1 / (1 + variance)  # lower variance = more AI-like


def entropy_analysis(text):
    diversity = lexical_diversity(text)
    fillers = filler_density(text)
    structure = structural_score(text)

    ai_bias = 0

    if diversity > 0.6:
        ai_bias += 20

    if fillers < 0.01:
        ai_bias += 20

    if structure > 0.5:
        ai_bias += 20

    return {
        "diversity": round(diversity, 2),
        "filler_density": round(fillers, 3),
        "structure_score": round(structure, 2),
        "ai_entropy_score": min(60, ai_bias)
    }