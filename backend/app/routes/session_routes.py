import os
import uuid
from flask import Blueprint, jsonify, request

session_bp = Blueprint("session", __name__, url_prefix="/session")

# Deployed candidate app URL (set via environment variable on Render)
CANDIDATE_APP_URL = os.environ.get("CANDIDATE_APP_URL", "https://ai-cheating-candidate-app.vercel.app")

@session_bp.route("/create", methods=["POST"])
def create_session():
    """Create new interview session"""
    
    session_id = "session_01"
    join_url = f"{CANDIDATE_APP_URL}?session={session_id}"
    
    print(f"✅ Created session: {session_id}")
    print(f"📋 Candidate link: {join_url}")
    
    return jsonify({
        "status": "success",
        "session_id": session_id,
        "join_url": join_url
    })