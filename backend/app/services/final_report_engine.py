import os

# Global in-memory session store
SESSION_EVENTS = {}

EVIDENCE_BASE_DIR = "backend/evidence"


def record_event(session_id: str, event_type: str):
    if session_id not in SESSION_EVENTS:
        SESSION_EVENTS[session_id] = {}
    
    events = SESSION_EVENTS[session_id]
    events[event_type] = events.get(event_type, 0) + 1


def get_evidence_files(session_id):
    folder = os.path.join(EVIDENCE_BASE_DIR, session_id)
    if not os.path.exists(folder):
        return []
    return [f for f in os.listdir(folder) if f.endswith(".jpg")]


def generate_final_report(session_id: str, fusion_state: dict):

    events = SESSION_EVENTS.get(session_id, {})
    phone = events.get("phone", 0)
    multi = events.get("multiple_person", 0)
    camera = events.get("camera", 0)
    looking = events.get("looking_away", 0)

    audio_ai_score = fusion_state.get("audio_score", 0)
    video_score = fusion_state.get("video_score", 0)

    # Calculate final risk (Weighted)
    risk = (
        phone * 50 +
        multi * 40 +
        camera * 30 +
        looking * 10 +
        audio_ai_score
    )

    risk = min(risk, 100)

    is_fail = risk > 60 or audio_ai_score > 70
    verdict = "FAIL (Suspicious Activity)" if is_fail else "PASS"

    # Specific reasons for fail
    status_msg = f"Final Risk Score: {risk}%"
    if audio_ai_score > 70:
        status_msg = "FAIL (AI Plagiarism Detected)"
    elif risk > 60:
        status_msg = "FAIL (Multiple Violations)"

    return {
        "session_id": session_id,
        "phone_events": phone,
        "multiple_person_events": multi,
        "camera_events": camera,
        "looking_away_events": looking,
        "ai_speech_score": audio_ai_score,
        "video_score": video_score,
        "evidence_files": get_evidence_files(session_id),
        "final_risk_score": int(risk),
        "verdict": verdict,
        "status_message": status_msg
    }