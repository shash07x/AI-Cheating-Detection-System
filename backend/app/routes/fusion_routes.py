from flask import Blueprint, jsonify, request
import time
from app.models.interview_session import InterviewSession
from app.extensions import db

fusion_bp = Blueprint("fusion", __name__, url_prefix="/analyze")

VIDEO_WEIGHT = 0.6
AUDIO_WEIGHT = 0.4
last_violation_time = None


@fusion_bp.route("/final", methods=["POST"])
def final_analysis():
    global last_violation_time

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    session_id = data.get("session_id", "default")

    video_score = data.get("video", {}).get("cheating_score", 0)
    audio_score = data.get("audio", {}).get("cheating_score", 0)

    final_score = int(video_score * VIDEO_WEIGHT + audio_score * AUDIO_WEIGHT)

    if final_score >= 80:
        violation_level = "critical"
    elif final_score >= 60:
        violation_level = "high"
    elif final_score >= 40:
        violation_level = "medium"
    else:
        violation_level = "low"

    now = time.time()
    escalation = False
    if violation_level in ["high", "critical"]:
        if last_violation_time and (now - last_violation_time < 30):
            escalation = True
        last_violation_time = now

    record = InterviewSession(
        session_id=session_id,
        video_score=video_score,
        audio_score=audio_score,
        final_score=final_score,
        violation_level=violation_level,
        escalation=escalation
    )

    db.session.add(record)
    db.session.commit()

    return jsonify({
        "final_analysis": {
            "session_id": session_id,
            "video_score": video_score,
            "audio_score": audio_score,
            "final_score": final_score,
            "violation_level": violation_level,
            "escalation": escalation
        },
        "status": "stored"
    })
