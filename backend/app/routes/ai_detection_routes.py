from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)

# Try to import database (optional - may not exist)
try:
    from app.extensions import db, socketio
    from app.models.interview_session import InterviewSession
    DB_AVAILABLE = True
except ImportError:
    from app.extensions import socketio
    DB_AVAILABLE = False
    logger.warning("Database not available - running without persistence")

from app.services.fraud_aggregator import aggregate_scores, explain
from app.services.fusion_state import get_state, reset_state
from app.services.answer_timeline import get_timeline, reset_timeline
from app.services.final_report_engine import generate_final_report
ai_bp = Blueprint("ai", __name__, url_prefix="/ai")

# --------------------------------------------------
# START SESSION
# --------------------------------------------------

@ai_bp.route("/start", methods=["POST"])
def start_session():
    """
    Start monitoring for an interview session.
    Resets timeline and fusion state.
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "session_01")

    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    try:
        logger.info(f"✅ Starting monitoring for session: {session_id}")

        # Reset answer timeline
        try:
            reset_timeline(session_id)
        except Exception as e:
            logger.warning(f"Timeline reset failed: {e}")

        # Reset fusion state (handle different signatures)
        try:
            reset_state(session_id)
        except TypeError:
            try:
                reset_state()
            except Exception as e:
                logger.warning(f"State reset failed: {e}")

        logger.info(f"✅ Monitoring started for session: {session_id}")

        return jsonify({
            "status": "success",
            "message": f"Monitoring started for session {session_id}",
            "session_id": session_id,
            "monitoring_active": True
        }), 200

    except Exception as e:
        logger.error(f"❌ Failed to start session {session_id}: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# --------------------------------------------------
# GET ANSWER TIMELINE
# --------------------------------------------------

@ai_bp.route("/answers/<session_id>", methods=["GET"])
def get_answers(session_id):
    """
    Get all answers recorded during the session.
    """
    try:
        answers = get_timeline(session_id)
        
        logger.info(f"Retrieved {len(answers)} answers for session {session_id}")
        
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "answers": answers,
            "count": len(answers)
        })
    
    except Exception as e:
        logger.error(f"Failed to get answers for {session_id}: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "session_id": session_id,
            "answers": []
        }), 500


# --------------------------------------------------
# GET SESSION TIMELINE (for graph)
# --------------------------------------------------

@ai_bp.route("/timeline/<session_id>", methods=["GET"])
def get_session_timeline(session_id):
    """
    Get timeline events for risk graph.
    """
    try:
        # Get timeline data
        timeline_data = get_timeline(session_id)
        
        # Format for graph
        events = []
        for i, answer in enumerate(timeline_data):
            events.append({
                "time": f"{i*5}:00",  # Mock timestamps
                "score": answer.get("ai_percent", 0),
                "level": "low" if answer.get("ai_percent", 0) < 40 else "medium" if answer.get("ai_percent", 0) < 70 else "high"
            })
        
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "events": events
        })
    
    except Exception as e:
        logger.error(f"Failed to get timeline for {session_id}: {e}")
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "events": []  # Return empty instead of error
        })


# --------------------------------------------------
# FINALIZE SESSION
# --------------------------------------------------

@ai_bp.route("/finalize", methods=["POST"])
def finalize_session():
    """
    Finalize interview session and generate final report.
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")

    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    try:
        logger.info(f"⏹ Finalizing session: {session_id}")

        # ---------------- BACKEND STATE ----------------
        state = get_state(session_id) or {}

        # Use PEAK scores (not last-frame snapshot) for the final report
        video_score = max(state.get("video_score", 0), state.get("max_video_score", 0))
        audio_score = max(state.get("audio_score", 0), state.get("max_audio_score", 0))
        tab_switches = state.get("tab_switches", 0)
        violation_count = state.get("violation_count", 0)

        logger.info(
            f"Session {session_id} scores: "
            f"video={video_score}, audio={audio_score}, tabs={tab_switches}, violations={violation_count}"
        )

        # ---------------- ANSWER TIMELINE ----------------
        answers = get_timeline(session_id)
        logger.info(f"Session {session_id} recorded {len(answers)} answers")

        # ---------------- AGGREGATE ----------------
        result = aggregate_scores(
            video_score=video_score,
            audio_score=audio_score,
            tab_switches=tab_switches
        )

        explanation = explain(video_score, audio_score)


        # ---------------- FINAL PAYLOAD ----------------
    
        auth_report = generate_final_report(session_id, state)
        payload = {
            "session_id": session_id,
            "video_score": video_score,
            "audio_score": audio_score,
            "tab_switches": tab_switches,
            "final_score": result["final_score"],
            "violation_level": result["violation_level"],
            "confidence": explanation.get("confidence", 0),
            "reasons": explanation.get("reasons", []),
            "escalation": result.get("escalation", False),
            "answers": answers,
            "answer_count": len(answers),

            # 🔥 Added
            "phone_events": auth_report["phone_events"],
            "multiple_person_events": auth_report["multiple_person_events"],
            "camera_events": auth_report["camera_events"],
            "looking_away_events": auth_report["looking_away_events"],
            "evidence_files": auth_report["evidence_files"],
            "final_risk_score": auth_report["final_risk_score"],
            "verdict": auth_report["verdict"]
        }
        # ---------------- STORE DB (OPTIONAL) ----------------
        if DB_AVAILABLE:
            try:
                record = InterviewSession(
                    session_id=session_id,
                    video_score=video_score,
                    audio_score=audio_score,
                    final_score=result["final_score"],
                    violation_level=result["violation_level"],
                    escalation=result.get("escalation", False)
                )
                db.session.add(record)
                db.session.commit()
                logger.info(f"✅ Saved session {session_id} to database")

            except Exception as db_error:
                logger.error(f"Database save failed: {db_error}")
                try:
                    db.session.rollback()
                except:
                    pass
                payload["db_warning"] = "Failed to save to database"
        else:
            logger.info("Database not available - skipping persistence")

        # ---------------- EMIT FINAL REPORT ----------------
        try:
            socketio.emit("final_report", payload)
            logger.info(f"✅ Emitted final_report for session {session_id}")
        except Exception as emit_error:
            logger.error(f"Failed to emit final_report: {emit_error}")

        # ---------------- CLEANUP ----------------
        try:
            reset_state(session_id)
        except TypeError:
            try:
                reset_state()
            except Exception as e:
                logger.warning(f"State cleanup failed: {e}")

        try:
            reset_timeline(session_id)
            logger.info(f"✅ Cleaned up session {session_id}")
        except Exception as e:
            logger.warning(f"Timeline cleanup failed: {e}")

        logger.info(f"✅ Session {session_id} finalized successfully")

        return jsonify({
            "status": "success",
            "message": "Session finalized successfully",
            "final_report": payload
        }), 200

    except Exception as e:
        logger.error(f"❌ Failed to finalize session {session_id}: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@ai_bp.route("/health", methods=["GET"])
def health_check():
    """
    Check if AI detection routes are working.
    """
    return jsonify({
        "status": "healthy",
        "service": "AI Detection Routes",
        "database_available": DB_AVAILABLE
    })