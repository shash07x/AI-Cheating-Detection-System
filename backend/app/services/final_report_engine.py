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

    # Use peak scores from the session (not last-frame values)
    audio_ai_score = max(
        fusion_state.get("audio_score", 0),
        fusion_state.get("max_audio_score", 0)
    )
    video_score = max(
        fusion_state.get("video_score", 0),
        fusion_state.get("max_video_score", 0)
    )
    violation_count = fusion_state.get("violation_count", 0)

    # Calculate final risk (Weighted — events + scores)
    risk = (
        phone * 50 +
        multi * 40 +
        camera * 30 +
        looking * 10 +
        audio_ai_score +
        int(video_score * 0.3)
    )

    risk = min(risk, 100)

    # Decision logic
    is_fail = risk > 60 or audio_ai_score > 70 or video_score > 80
    is_review = not is_fail and (risk > 30 or video_score > 50 or violation_count > 5)
    
    if is_fail:
        verdict = "FAIL (Suspicious Activity)"
    elif is_review:
        verdict = "REVIEW"
    else:
        verdict = "PASS"

    # Specific reasons
    status_msg = f"Final Risk Score: {risk}%"
    if audio_ai_score > 70:
        status_msg = "FAIL (AI Plagiarism Detected)"
    elif video_score > 80:
        status_msg = "FAIL (Critical Video Violations)"
    elif risk > 60:
        status_msg = "FAIL (Multiple Violations)"
    elif is_review:
        status_msg = "REVIEW (Moderate Violations Detected)"

    return {
        "session_id": session_id,
        "phone_events": phone,
        "multiple_person_events": multi,
        "camera_events": camera,
        "looking_away_events": looking,
        "ai_speech_score": audio_ai_score,
        "video_score": video_score,
        "violation_count": violation_count,
        "evidence_files": get_evidence_files(session_id),
        "final_risk_score": int(risk),
        "verdict": verdict,
        "status_message": status_msg
    }