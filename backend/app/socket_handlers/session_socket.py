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