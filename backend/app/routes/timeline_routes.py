from flask import Blueprint, jsonify
from app.services.fusion_state import get_timeline

timeline_bp = Blueprint("timeline", __name__, url_prefix="/timeline")

@timeline_bp.route("/<session_id>", methods=["GET"])
def fetch_timeline(session_id):
    timeline = get_timeline(session_id)
    return jsonify({
        "session_id": session_id,
        "events": timeline
    })
