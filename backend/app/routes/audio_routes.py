"""
Audio Routes - HTTP endpoints for audio analysis

Supports:
  1. Audio chunk analysis via Enhanced Audio Engine (EAAE)
  2. AI text detection via Gemini + Canary transcription
  3. Session management (reset)
"""

from flask import Blueprint, jsonify, request
import numpy as np
import soundfile as sf
import io
import time

from app.services.enhanced_audio_engine import analyze_audio_chunk, reset_audio_session
from app.services.ai_text_detector import detect_ai_text, get_session_ai_summary, reset_session_detection
from app.utils.logger import logger

audio_bp = Blueprint("audio", __name__, url_prefix="/audio")


# ---------- NORMALIZATION ----------
def normalize(obj):
    """Converts numpy/torch/bool objects into JSON-safe Python types"""
    if isinstance(obj, dict):
        return {k: normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize(v) for v in obj]
    if hasattr(obj, "item"):
        return obj.item()
    return obj


@audio_bp.route("/analyze", methods=["POST"])
def analyze_audio():
    """
    Analyze audio chunk using Enhanced Audio Engine (EAAE)
    """
    logger.info("🔊 Audio analysis request received")

    # ---------- INPUT VALIDATION ----------
    if "audio" not in request.files:
        logger.warning("❌ No audio file in request")
        return jsonify({"error": "No audio provided"}), 400

    if "session_id" not in request.form:
        logger.warning("❌ No session_id in request")
        return jsonify({"error": "No session_id provided"}), 400

    audio_file = request.files["audio"]
    session_id = request.form.get("session_id")
    audio_bytes = audio_file.read()

    if not audio_bytes:
        logger.warning("❌ Empty audio file uploaded")
        return jsonify({"error": "Empty audio file"}), 400

    # ---------- AUDIO VALIDATION ----------
    try:
        audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))
        logger.info(f"✅ Audio loaded | Sample rate: {sample_rate} | Duration: {len(audio_data)/sample_rate:.2f}s")
    except Exception as e:
        logger.error(f"❌ Audio loading failed: {e}", exc_info=True)
        return jsonify({
            "error": "Invalid audio format",
            "details": str(e)
        }), 400

    # Ensure mono audio
    if isinstance(audio_data, np.ndarray) and audio_data.ndim > 1:
        audio_data = np.mean(audio_data, axis=1)
        logger.info("🔄 Converted stereo audio to mono")

    # ---------- EAAE ANALYSIS ----------
    try:
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sample_rate, format='WAV')
        audio_bytes_converted = audio_buffer.getvalue()

        eaae_analysis = analyze_audio_chunk(
            audio_bytes=audio_bytes_converted,
            session_id=session_id,
            sr=sample_rate
        )

        logger.info(
            f"🎙️ EAAE Analysis: {eaae_analysis.detection_type} | "
            f"Alert: {eaae_analysis.alert_level} | Score: {eaae_analysis.score}"
        )

        # Convert alert level
        alert_level_str = str(eaae_analysis.alert_level).lower().replace("audialertlevel.", "")
        if alert_level_str == "none":
            alert_level_str = "low"

        # Map confidence
        if alert_level_str == "critical":
            confidence = 95
        elif alert_level_str == "medium":
            confidence = 75
        else:
            confidence = 50

        # Build response
        response = {
            "analysis": {
                "detection_type": eaae_analysis.detection_type,
                "reason": eaae_analysis.reason,
                "cheating_score": eaae_analysis.score,
                "violation_level": alert_level_str,
                "confidence": confidence,
                "is_ai_voice": eaae_analysis.is_ai_voice,
                "background_noise_level": eaae_analysis.background_noise_level,
                "silence_ratio": eaae_analysis.silence_ratio,
            },
            "status": "processed"
        }

        logger.info(
            f"✅ Audio analysis completed | "
            f"Score={eaae_analysis.score} | Level={alert_level_str}"
        )

        return jsonify(normalize(response))

    except Exception as e:
        logger.error(f"❌ EAAE analysis error: {e}", exc_info=True)
        return jsonify({
            "error": "Audio analysis failed",
            "details": str(e)
        }), 500


@audio_bp.route("/detect-ai", methods=["POST"])
def detect_ai_in_text():
    """
    Detect AI-generated text using Gemini + Heuristic analysis.

    Expects JSON:
    {
        "text": "transcript text",
        "session_id": "session_01"
    }
    """
    try:
        data = request.json

        if not data or "text" not in data:
            return jsonify({"error": "No text provided"}), 400

        text = data["text"]
        session_id = data.get("session_id", "default")

        result = detect_ai_text(
            transcript=text,
            session_id=session_id,
            use_gemini=True
        )

        return jsonify(normalize(result))

    except Exception as e:
        logger.error(f"❌ AI detection error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@audio_bp.route("/ai-summary/<session_id>", methods=["GET"])
def ai_detection_summary(session_id):
    """Get AI detection summary for a session."""
    try:
        summary = get_session_ai_summary(session_id)
        return jsonify(summary)
    except Exception as e:
        logger.error(f"❌ AI summary error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@audio_bp.route("/reset/<session_id>", methods=["POST"])
def reset_audio_session_route(session_id):
    """Reset audio session state for a given session_id"""
    try:
        reset_audio_session(session_id)
        reset_session_detection(session_id)
        logger.info(f"🔄 Audio session reset for {session_id}")
        return jsonify({"status": "reset", "session_id": session_id})
    except Exception as e:
        logger.error(f"❌ Audio reset error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
