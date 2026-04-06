import time
from collections import defaultdict

ANSWER_TIMELINE = defaultdict(list)

SEGMENT_DURATION = 15  # seconds


def record_answer(
    session_id,
    transcript,
    audio_score,
    linguistic_score,
    ai_score,
    whisper_score
):
    entry = {
        "timestamp": time.time(),
        "transcript": transcript[:300],
        "audio_score": audio_score,
        "linguistic_score": linguistic_score,
        "ai_voice_score": ai_score,
        "whisper_score": whisper_score,
        "authenticity": max(audio_score, linguistic_score, ai_score, whisper_score)
    }

    ANSWER_TIMELINE[session_id].append(entry)

def add_answer(session_id, answer):

    ANSWER_TIMELINE[session_id].append(answer)

def get_timeline(session_id):
    return ANSWER_TIMELINE.get(session_id, [])


def reset_timeline(session_id):
    ANSWER_TIMELINE[session_id]=[]
