from app.extensions import db
from datetime import datetime

class AudioAnalysis(db.Model):
    __tablename__ = "audio_analysis"

    id = db.Column(db.Integer, primary_key=True)
    cheating_score = db.Column(db.Integer, nullable=False)
    violation_level = db.Column(db.String(20), nullable=False)

    whisper_detected = db.Column(db.Boolean, default=False)
    speaker_mismatch = db.Column(db.Boolean, default=False)
    ai_voice_detected = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
