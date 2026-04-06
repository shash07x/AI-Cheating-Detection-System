from collections import defaultdict, deque
import time
import numpy as np

# -----------------------------
# FUSION STATE (PER SESSION)
# -----------------------------

STATE = defaultdict(lambda: {
    "video_score": 0,
    "audio_score": 0,
    "final_score": 0,
    "max_score": 0,
    "tab_switches": 0,
    "timeline": deque(maxlen=300),
    "voice_embedding": None,
    "voice_drift_score": 0,
})

# -----------------------------
# VOICE DRIFT DETECTION
# -----------------------------

def update_voice_embedding(session_id, new_embedding):
    state = STATE[session_id]

    if state["voice_embedding"] is None:
        state["voice_embedding"] = new_embedding
        return 0

    baseline = state["voice_embedding"]

    similarity = np.dot(baseline, new_embedding) / (
        np.linalg.norm(baseline) * np.linalg.norm(new_embedding) + 1e-8
    )

    drift = 1 - similarity
    state["voice_drift_score"] = drift

    # adaptive baseline update
    state["voice_embedding"] = 0.9 * baseline + 0.1 * new_embedding

    return drift


# -----------------------------
# UPDATE FUNCTIONS
# -----------------------------

def update_video(session_id, score):
    STATE[session_id]["video_score"] = score


def update_audio(session_id, score):
    state = STATE[session_id]

    drift_penalty = int(state["voice_drift_score"] * 50)

    state["audio_score"] = min(100, score + drift_penalty)


def update_tab_switch(session_id):
    STATE[session_id]["tab_switches"] += 1


# -----------------------------
# FUSION ENGINE
# -----------------------------

def aggregate_scores(session_id):

    state = STATE[session_id]

    video_score = state["video_score"]
    audio_score = state["audio_score"]
    tab_switches = state["tab_switches"]

    tab_penalty = min(20, tab_switches * 5)

    final_score = max(video_score, audio_score) + tab_penalty
    final_score = min(100, final_score)

    state["final_score"] = final_score

    # track highest score seen
    state["max_score"] = max(state["max_score"], final_score)

    violation_level = _map_violation_level(final_score)

    add_timeline_event(session_id, final_score, violation_level)

    return {
        "video_score": video_score,
        "audio_score": audio_score,
        "final_score": final_score,
        "max_score": state["max_score"],
        "violation_level": violation_level
    }


# -----------------------------
# TIMELINE
# -----------------------------

def add_timeline_event(session_id, final_score, violation_level):

    STATE[session_id]["timeline"].append({
        "time": time.time(),
        "final_score": final_score,
        "violation_level": violation_level
    })


# -----------------------------
# GETTERS
# -----------------------------

def get_state(session_id):
    return STATE[session_id]


def get_timeline(session_id):
    return list(STATE[session_id]["timeline"])


# -----------------------------
# FINAL DECISION LOGIC
# -----------------------------

def get_final_decision(session_id):

    state = STATE[session_id]

    max_score = state["max_score"]
    audio_score = state["audio_score"]

    # 🔥 NEW RULE
    # Immediate FAIL if AI plagiarism detected
    if audio_score >= 70:
        return {
            "decision": "FAIL",
            "reason": "AI-generated answers detected",
            "audio_score": audio_score,
            "max_score": max_score
        }

    # Standard rules
    if max_score >= 90:
        decision = "FAIL"

    elif max_score >= 70:
        decision = "REVIEW"

    else:
        decision = "PASS"

    return {
        "decision": decision,
        "max_score": max_score,
        "audio_score": audio_score
    }


# -----------------------------
# RESET
# -----------------------------

def reset_state(session_id):
    STATE.pop(session_id, None)


# -----------------------------
# VIOLATION LEVEL MAPPER
# -----------------------------

def _map_violation_level(score):

    if score >= 90:
        return "critical"

    elif score >= 70:
        return "high"

    elif score >= 40:
        return "medium"

    elif score > 0:
        return "low"

    return "none"