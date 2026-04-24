"""
MongoDB Service - Session Data Persistence

Connects to MongoDB Atlas and stores proctoring session results.
Gracefully degrades: if MongoDB is unavailable, the app runs without persistence.
"""

import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ================================================
# MODULE STATE
# ================================================

_client = None
_db = None
MONGO_AVAILABLE = False


def init_mongo(app=None):
    """
    Initialize MongoDB connection.
    Call during app startup. If connection fails, app continues without persistence.
    """
    global _client, _db, MONGO_AVAILABLE

    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure

        mongo_uri = os.environ.get("MONGO_URI", "")

        if not mongo_uri:
            logger.warning("⚠️ MONGO_URI not set — running without MongoDB persistence")
            return

        # Connect with a short timeout so startup isn't blocked
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

        # Verify connection
        _client.admin.command("ping")

        _db = _client.get_database("proctoring")
        MONGO_AVAILABLE = True

        logger.info("✅ MongoDB Atlas connected — database: proctoring")

        # Ensure index on session_id for fast lookups
        _db.sessions.create_index("session_id", unique=True)
        logger.info("✅ MongoDB indexes created")

    except ImportError:
        logger.warning("⚠️ pymongo not installed — running without MongoDB")
    except Exception as e:
        logger.warning(f"⚠️ MongoDB connection failed: {e} — running without persistence")
        MONGO_AVAILABLE = False


# ================================================
# SESSION START
# ================================================

def record_session_start(session_id: str, candidate_id: str = ""):
    """
    Record session start time and candidate_id.
    Creates or updates the document with first_record_time.
    """
    if not MONGO_AVAILABLE or _db is None:
        return

    try:
        now = datetime.now(timezone.utc)

        _db.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "candidate_id": candidate_id,
                    "first_record_time": now,
                    "status": "active",
                },
                "$setOnInsert": {
                    "session_id": session_id,
                    "created_at": now,
                    "video_score": 0,
                    "audio_score": 0,
                    "speech_auth_score": 0,
                    "final_score": 0,
                    "violation_count": 0,
                    "tab_switches": 0,
                    "violation_level": "none",
                    "verdict": "",
                    "session_duration": 0,
                }
            },
            upsert=True
        )
        logger.info(f"✅ MongoDB: session {session_id} started (candidate={candidate_id})")

    except Exception as e:
        logger.error(f"❌ MongoDB record_session_start failed: {e}")


# ================================================
# SAVE SESSION RESULT
# ================================================

def save_session_result(
    session_id: str,
    candidate_id: str = "",
    video_score: int = 0,
    audio_score: int = 0,
    speech_auth_score: int = 0,
    final_score: int = 0,
    violation_count: int = 0,
    tab_switches: int = 0,
    violation_level: str = "none",
    verdict: str = "",
):
    """
    Save the final session result to MongoDB.
    Calculates session_duration as last_update_time - first_record_time.
    """
    if not MONGO_AVAILABLE or _db is None:
        logger.info("MongoDB not available — skipping session save")
        return None

    try:
        now = datetime.now(timezone.utc)

        # Get existing document to calculate duration
        existing = _db.sessions.find_one({"session_id": session_id})
        first_time = existing.get("first_record_time", now) if existing else now
        duration = (now - first_time).total_seconds()

        result = _db.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "candidate_id": candidate_id or (existing.get("candidate_id", "") if existing else ""),
                    "video_score": video_score,
                    "audio_score": audio_score,
                    "speech_auth_score": speech_auth_score,
                    "final_score": final_score,
                    "violation_count": violation_count,
                    "tab_switches": tab_switches,
                    "violation_level": violation_level,
                    "verdict": verdict,
                    "session_duration": round(duration, 2),
                    "last_update_time": now,
                    "status": "completed",
                }
            },
            upsert=True
        )

        logger.info(
            f"✅ MongoDB: session {session_id} saved — "
            f"video={video_score}, audio={audio_score}, final={final_score}, "
            f"violations={violation_count}, tabs={tab_switches}, "
            f"duration={duration:.1f}s, verdict={verdict}"
        )
        return result

    except Exception as e:
        logger.error(f"❌ MongoDB save_session_result failed: {e}")
        return None


# ================================================
# QUERY SESSIONS
# ================================================

def get_all_sessions():
    """Get all stored sessions (for dashboard history)."""
    if not MONGO_AVAILABLE or _db is None:
        return []

    try:
        sessions = list(_db.sessions.find(
            {},
            {"_id": 0}  # Exclude MongoDB _id field
        ).sort("created_at", -1).limit(100))

        # Convert datetime objects to ISO strings for JSON serialization
        for s in sessions:
            for key in ("first_record_time", "last_update_time", "created_at"):
                if key in s and isinstance(s[key], datetime):
                    s[key] = s[key].isoformat()

        return sessions

    except Exception as e:
        logger.error(f"❌ MongoDB get_all_sessions failed: {e}")
        return []


def get_session(session_id: str):
    """Get a single session by ID."""
    if not MONGO_AVAILABLE or _db is None:
        return None

    try:
        doc = _db.sessions.find_one(
            {"session_id": session_id},
            {"_id": 0}
        )
        if doc:
            for key in ("first_record_time", "last_update_time", "created_at"):
                if key in doc and isinstance(doc[key], datetime):
                    doc[key] = doc[key].isoformat()
        return doc

    except Exception as e:
        logger.error(f"❌ MongoDB get_session failed: {e}")
        return None
