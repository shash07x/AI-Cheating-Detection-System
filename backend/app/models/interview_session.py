from datetime import datetime
from app.extensions import db

class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"
    __table_args__ = {"extend_existing": True}  # 🔑 CRITICAL FIX

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, unique=True)

    video_score = db.Column(db.Integer, default=0)
    audio_score = db.Column(db.Integer, default=0)
    final_score = db.Column(db.Integer, default=0)

    violation_level = db.Column(db.String(20), default="low")
    escalation = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
