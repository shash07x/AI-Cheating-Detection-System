from flask import Blueprint, jsonify, request
from app.extensions import db

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/sessions", methods=["GET"])
def dashboard_summary():
    from app.models.interview_session import InterviewSession  # lazy import

    total = InterviewSession.query.count()

    critical = InterviewSession.query.filter_by(
        violation_level="critical"
    ).count()

    high = InterviewSession.query.filter_by(
        violation_level="high"
    ).count()

    escalations = InterviewSession.query.filter_by(
        escalation=True
    ).count()

    return jsonify({
        "total_sessions": total,
        "critical_cases": critical,
        "high_risk_cases": high,
        "escalations": escalations
    })
def get_sessions():
    """
    Fetch all interview sessions
    Optional filters:
      - violation_level
      - escalation (true / false)
    """

    from app.models.interview_session import InterviewSession  # lazy import

    violation = request.args.get("violation_level")
    escalation = request.args.get("escalation")

    query = InterviewSession.query

    if violation:
        query = query.filter_by(violation_level=violation)

    if escalation is not None:
        query = query.filter_by(escalation=escalation.lower() == "true")

    sessions = query.order_by(
        InterviewSession.created_at.desc()
    ).all()

    results = []
    for s in sessions:
        results.append({
            "session_id": s.session_id,
            "video_score": s.video_score,
            "audio_score": s.audio_score,
            "final_score": s.final_score,
            "violation_level": s.violation_level,
            "escalation": s.escalation,
            "created_at": s.created_at.isoformat()
        })

    return jsonify({
        "count": len(results),
        "sessions": results
    })
