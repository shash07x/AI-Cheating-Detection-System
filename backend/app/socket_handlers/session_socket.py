from app.extensions import socketio
from app.services.fusion_state import get_state
import logging
from flask import request

logger = logging.getLogger(__name__)

# PRE-AUTHORIZE session_01
SESSION_ROLES = {
    "session_01": {
        "candidate": "ANY",
        "interviewer": "ANY"
    }
}

# Track candidates waiting for admission
PENDING_CANDIDATES = {}

@socketio.on("connect")
def handle_connect():
    logger.info(f"✅ Client connected: {request.sid}")
    # Auto-register for session_01
    SESSION_ROLES["session_01"]["candidate"] = request.sid
    SESSION_ROLES["session_01"]["interviewer"] = request.sid
    logger.info(f"Auto-registered {request.sid} for session_01")

@socketio.on("register_role")
def register_role(data):
    session_id = data.get("session_id", "session_01")
    role = data.get("role", "candidate")
    
    if session_id not in SESSION_ROLES:
        SESSION_ROLES[session_id] = {}
    
    SESSION_ROLES[session_id][role] = request.sid
    logger.info(f"🔐 {role} registered: {request.sid}")

@socketio.on("join_session")
def join_session(data):
    session_id = data.get("session_id", "session_01")
    role = data.get("role", "candidate")
    
    if session_id not in SESSION_ROLES:
        SESSION_ROLES[session_id] = {}
    
    SESSION_ROLES[session_id][role] = request.sid
    logger.info(f"✅ {role} joined {session_id}")

@socketio.on("ping")
def handle_ping(data):
    """Handle keep-alive ping"""
    socketio.emit("pong", {"timestamp": data.get("timestamp")})

# ================= CANDIDATE ADMISSION FLOW =================

@socketio.on("candidate_join_request")
def handle_join_request(data):
    """Candidate requests to join — forward to interviewer dashboard"""
    candidate_id = data.get("candidate_id", "")
    session_id = data.get("session_id", "session_01")
    candidate_sid = request.sid

    logger.info(f"📩 Candidate join request: {candidate_id} for {session_id} (sid={candidate_sid})")

    # Store the mapping so we can route the response back
    PENDING_CANDIDATES[candidate_id] = {
        "sid": candidate_sid,
        "session_id": session_id,
    }

    # Broadcast to all connected clients (interviewer dashboard will pick it up)
    socketio.emit("candidate_join_request", {
        "candidate_id": candidate_id,
        "session_id": session_id,
    })

@socketio.on("candidate_admission_response")
def handle_admission_response(data):
    """Interviewer accepts/declines — forward to the specific candidate"""
    candidate_id = data.get("candidate_id", "")
    admitted = data.get("admitted", False)
    reason = data.get("reason", "")

    logger.info(f"📤 Admission response for {candidate_id}: admitted={admitted}")

    pending = PENDING_CANDIDATES.pop(candidate_id, None)
    if pending:
        # Send response only to the candidate who requested
        socketio.emit("admission_response", {
            "candidate_id": candidate_id,
            "session_id": pending["session_id"],
            "admitted": admitted,
            "reason": reason,
        }, to=pending["sid"])
    else:
        # Fallback: broadcast in case SID mapping was lost
        logger.warning(f"⚠️ No pending record for {candidate_id}, broadcasting response")
        socketio.emit("admission_response", {
            "candidate_id": candidate_id,
            "session_id": data.get("session_id", "session_01"),
            "admitted": admitted,
            "reason": reason,
        })

# ================= RISK UPDATES =================

def emit_risk_update(session_id):
    """Emit risk update to dashboard"""
    state = get_state(session_id)
    
    payload = {
        "session_id": session_id,
        "video_score": state.get("video_score", 0),
        "audio_score": state.get("audio_score", 0),
        "final_score": max(state.get("video_score", 0), state.get("audio_score", 0))
    }
    
    logger.info(f"📡 RISK UPDATE: {payload}")
    socketio.emit("risk_update", payload)