import uuid
from flask import Blueprint, jsonify, request

session_bp = Blueprint("session", __name__, url_prefix="/session")

@session_bp.route("/create", methods=["POST"])
def create_session():
    """Create new interview session"""
    
    session_id = "session_01"
    join_url = f"http://localhost:3001?session={session_id}"
    
    print(f"✅ Created session: {session_id}")
    
    return jsonify({
        "status": "success",
        "session_id": session_id,
        "join_url": join_url
    })