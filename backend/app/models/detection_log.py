from app.utils.database import db
from app.utils.helpers import current_time

def log_event(session_id, event_type, confidence):
    db.logs.insert_one({
        "session_id": session_id,
        "event": event_type,
        "confidence": confidence,
        "timestamp": current_time()
    })
