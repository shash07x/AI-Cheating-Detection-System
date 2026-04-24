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
    tab_switches = fusion_state.get("tab_switches", 0)
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

    # ============================================================
    # STRICT VERDICT LOGIC
    # FAIL if ANY of these conditions are true:
    #   - Tab switches > 3
    #   - Phone detected (any)
    #   - Multiple persons detected (any)
    #   - Camera violations detected (any)
    #   - Video score > 60 (high suspicion)
    #   - Audio AI score > 60 (likely AI-generated speech)
    #   - Risk score > 50
    # REVIEW if moderate issues detected
    # PASS only if everything is clean and low
    # ============================================================

    fail_reasons = []

    if tab_switches > 3:
        fail_reasons.append(f"Excessive tab switches ({tab_switches})")
    if phone > 0:
        fail_reasons.append(f"Phone detected ({phone} times)")
    if multi > 0:
        fail_reasons.append(f"Multiple persons detected ({multi} times)")
    if camera > 0:
        fail_reasons.append(f"Camera violations ({camera} times)")
    if video_score > 60:
        fail_reasons.append(f"High video risk score ({video_score}%)")
    if audio_ai_score > 60:
        fail_reasons.append(f"AI-generated speech detected ({audio_ai_score}%)")
    if risk > 50:
        fail_reasons.append(f"High overall risk ({risk}%)")

    review_reasons = []

    if looking > 5:
        review_reasons.append(f"Frequent looking away ({looking} times)")
    if video_score > 40:
        review_reasons.append(f"Moderate video risk ({video_score}%)")
    if audio_ai_score > 30:
        review_reasons.append(f"Moderate AI speech score ({audio_ai_score}%)")
    if tab_switches > 1:
        review_reasons.append(f"Multiple tab switches ({tab_switches})")
    if violation_count > 3:
        review_reasons.append(f"Multiple violations ({violation_count})")

    # Decision
    if fail_reasons:
        verdict = "FAIL"
        status_msg = "FAIL: " + "; ".join(fail_reasons[:3])
    elif review_reasons:
        verdict = "REVIEW"
        status_msg = "REVIEW: " + "; ".join(review_reasons[:3])
    else:
        verdict = "PASS"
        status_msg = "PASS: No suspicious activity detected"

    return {
        "session_id": session_id,
        "phone_events": phone,
        "multiple_person_events": multi,
        "camera_events": camera,
        "looking_away_events": looking,
        "ai_speech_score": audio_ai_score,
        "video_score": video_score,
        "tab_switches": tab_switches,
        "violation_count": violation_count,
        "evidence_files": get_evidence_files(session_id),
        "final_risk_score": int(risk),
        "verdict": verdict,
        "status_message": status_msg,
        "fail_reasons": fail_reasons,
        "review_reasons": review_reasons
    }
