"""
Audio Socket Handler - Real-time Audio Analysis Pipeline

Pipeline:
  1. Receive audio chunks via WebSocket (WebM/Opus format from browser)
  2. Decode WebM → PCM float32 using PyAV
  3. Buffer speech segments
  4. Transcribe using Whisper (or basic energy fallback)
  5. Detect AI-generated text using Gemini + Heuristics
  6. Emit real-time scores to interviewer dashboard
"""

import base64
import io
import numpy as np
from collections import defaultdict, deque
import logging
from flask import request
import time

from app.extensions import socketio
from app.services.fusion_state import update_audio, get_state

logger = logging.getLogger(__name__)

# ================================================
# SESSION STATE
# ================================================

SESSION_AUDIO_STATE = defaultdict(lambda: {
    "scores": deque(maxlen=10),
    "last_emit_time": 0,
    "chunk_count": 0,
    "is_currently_speaking": False,
    "speech_buffer": [],      # list of float32 numpy arrays
    "silence_count": 0,
    "full_transcript": "",
    "last_gemini_analysis": None,
    "detection_history": []
})

SAMPLE_RATE = 16000
EMIT_INTERVAL = 0.5
# ============================================================
# SILENCE THRESHOLD: This is the critical value.
# WebM/Opus digital silence has RMS ~0.0001–0.002 (ambient noise floor).
# Microphone ambient noise measured at ~0.011–0.013 RMS.
# Real human speech typically has RMS ~0.03–0.15.
# We set threshold at 0.015 to filter ambient noise while catching all speech.
# ============================================================
SILENCE_THRESHOLD = 0.015
SPEECH_BUFFER_SIZE = 1      # 1 × 2s chunk = 2s of audio before analysis
SILENCE_RESET_COUNT = 3     # After 3 silence chunks, force audio score to 0


# ================================================
# WEBM → PCM DECODER
# ================================================

def _decode_webm_to_pcm(audio_bytes: bytes) -> np.ndarray:
    """
    Decode WebM/Opus (or any container) bytes to a float32 mono PCM array at 16 kHz.
    Uses PyAV for decoding then scipy/numpy for resampling.
    Returns a float32 numpy array, or None on failure.
    """
    try:
        import av

        buf = io.BytesIO(audio_bytes)
        container = av.open(buf, format=None)   # let av auto-detect format

        pcm_chunks = []
        for frame in container.decode(audio=0):
            arr = frame.to_ndarray()             # shape varies by format

            fmt_name = frame.format.name if frame.format else "unknown"

            # PyAV returns planar float (fltp) for Opus — shape is (channels, samples)
            # Values are already in [-1, 1].
            # For packed int16/s16, shape is (1, samples*channels) and needs normalisation.
            if arr.ndim == 2:
                # Planar layout: (channels, samples)
                arr = arr.mean(axis=0)           # mix to mono
            # else arr is already 1-D

            arr = arr.astype(np.float32)

            # Normalise int16 packed formats to [-1, 1]
            if fmt_name in ("s16", "s16p", "s32", "s32p"):
                if fmt_name in ("s16", "s16p"):
                    arr = arr / 32768.0
                else:
                    arr = arr / 2147483648.0
            # fltp / flt are already [-1, 1] – no scaling needed

            pcm_chunks.append(arr)

        if not pcm_chunks:
            return None

        pcm = np.concatenate(pcm_chunks)

        # Resample to 16 kHz if the container SR differs
        src_sr = 48000  # default Opus SR
        try:
            if container.streams.audio:
                src_sr = container.streams.audio[0].codec_context.sample_rate or 48000
        except Exception:
            pass

        if src_sr != SAMPLE_RATE and src_sr > 0:
            try:
                import librosa
                pcm = librosa.resample(pcm, orig_sr=src_sr, target_sr=SAMPLE_RATE)
            except Exception:
                # Manual linear downsampling fallback
                ratio = src_sr / SAMPLE_RATE
                new_len = max(1, int(len(pcm) / ratio))
                indices = np.linspace(0, len(pcm) - 1, new_len).astype(int)
                pcm = pcm[indices]

        # Clip to [-1, 1]
        pcm = np.clip(pcm, -1.0, 1.0)
        logger.debug(f"WebM decode OK: {len(pcm)} samples @ {SAMPLE_RATE}Hz, RMS={np.sqrt(np.mean(pcm**2)):.4f}")
        return pcm

    except Exception as e:
        logger.info(f"WebM decode via av failed: {e}, falling back to raw int16")
        return None


def _decode_raw_pcm(audio_bytes: bytes) -> np.ndarray:
    """
    Fallback: treat bytes as raw PCM int16.
    If the length is odd, trim the last byte.
    """
    try:
        if len(audio_bytes) % 2 != 0:
            audio_bytes = audio_bytes[:-1]
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
        return audio_np.astype(np.float32) / 32768.0
    except Exception as e:
        logger.error(f"Raw PCM decode failed: {e}")
        return None


def _looks_like_webm(audio_bytes: bytes) -> bool:
    """Check if bytes start with EBML header (WebM/Matroska signature)."""
    return len(audio_bytes) > 4 and audio_bytes[:4] == b'\x1a\x45\xdf\xa3'


def decode_audio(audio_bytes: bytes, is_webm: bool = False) -> np.ndarray:
    """
    Main decoder with robust format detection.

    When the data is known to NOT be WebM (raw PCM int16 from MicrophoneSender),
    we decode as raw PCM FIRST. This avoids PyAV on HF Spaces misinterpreting
    raw int16 bytes as an audio container, which produces garbage data with
    near-zero RMS and causes false silence detection.
    """
    # Auto-detect: check EBML magic bytes regardless of the is_webm flag
    has_webm_signature = _looks_like_webm(audio_bytes)

    if has_webm_signature or is_webm:
        # Data IS a WebM/Opus container → try WebM decode first
        logger.debug("🎤 [AUDIO] Detected WebM/container data, using av decoder")
        pcm = _decode_webm_to_pcm(audio_bytes)
        if pcm is not None and len(pcm) > 500:
            return pcm
        # WebM decode failed → DON'T fall back to raw PCM (garbage)
        logger.warning("🎤 [AUDIO] WebM decode failed and raw PCM fallback disabled for WebM data")
        return None
    else:
        # Data is raw PCM int16 → decode directly, skip PyAV entirely
        logger.debug("🎤 [AUDIO] Raw PCM data detected, using direct int16 decoder")
        pcm = _decode_raw_pcm(audio_bytes)
        if pcm is not None and len(pcm) > 500:
            return pcm
        # Raw PCM failed → try WebM as last resort
        logger.info("🎤 [AUDIO] Raw PCM decode failed, trying WebM as fallback")
        pcm = _decode_webm_to_pcm(audio_bytes)
        if pcm is not None and len(pcm) > 500:
            return pcm
        return None


# ================================================
# AUDIO CHUNK HANDLER
# ================================================

@socketio.on("audio_chunk")
def handle_audio_chunk(data):

    try:
        session_id = data.get("session_id", "session_01")
        audio_b64 = data.get("audio")

        if not audio_b64:
            logger.warning("⚠️ [AUDIO] Received audio_chunk event but no audio data!")
            return

        state = SESSION_AUDIO_STATE[session_id]
        state["chunk_count"] += 1

        logger.info(f"🎤 [AUDIO] Received chunk #{state['chunk_count']} for {session_id} | b64 len={len(audio_b64)}")

        # ==================
        # DECODE AUDIO
        # ==================
        is_webm = False
        try:
            if isinstance(audio_b64, str):
                if audio_b64.startswith("data:"):
                    # Check if this is WebM data
                    header = audio_b64.split(",", 1)[0].lower()
                    is_webm = "webm" in header or "opus" in header
                    audio_b64 = audio_b64.split(",", 1)[1]
                audio_bytes = base64.b64decode(audio_b64)
                logger.info(f"🎤 [AUDIO] Decoded {len(audio_bytes)} bytes from base64 (webm={is_webm})")
        except Exception as e:
            logger.error(f"Base64 decode error: {e}")
            return

        # ==========================================
        # CONVERT TO FLOAT32 PCM (handle WebM/Opus)
        # ==========================================
        audio_float = decode_audio(audio_bytes, is_webm=is_webm)

        if audio_float is None or audio_float.size < 100:
            logger.warning(f"🎤 [AUDIO] Decode FAILED or too short: {'None' if audio_float is None else f'{audio_float.size} samples'}")
            return

        rms = float(np.sqrt(np.mean(audio_float ** 2)))
        logger.info(f"🎤 [AUDIO] chunk #{state['chunk_count']} | samples={len(audio_float)} | rms={rms:.6f} | threshold={SILENCE_THRESHOLD}")

        # ==================
        # SILENCE DETECTION
        # ==================
        if rms < SILENCE_THRESHOLD:

            state["silence_count"] += 1
            state["is_currently_speaking"] = False

            # After enough silence, reset audio score to 0
            if state["silence_count"] >= SILENCE_RESET_COUNT:
                update_audio(session_id, 0)

            # When silent, show 0/0 (no speech to analyze)
            socketio.emit("ai_live_update", {
                "session_id": session_id,
                "status": "waiting_for_speech",
                "ai_percent": 0,
                "human_percent": 0,
                "is_speaking": False
            })

            # Push audio_score=0 via risk_update so the dashboard resets
            fusion_state = get_state(session_id)
            video_score = fusion_state.get("video_score", 0)
            socketio.emit("risk_update", {
                "session_id": session_id,
                "video_score": video_score,
                "audio_score": 0,
                "final_score": video_score,
                "violation_level": "low" if video_score < 40 else "medium"
            })
            return

        # ==================
        # SPEECH DETECTED
        # ==================
        state["silence_count"] = 0
        state["is_currently_speaking"] = True
        state["speech_buffer"].append(audio_float)   # store float32 array

        # =========================================================
        # IMMEDIATE ENERGY-BASED SCORE — shows speech is happening
        # rms 0.008–0.15 for normal speech → map to AI risk 5–20
        # This is a BASELINE "human speech detected" indicator.
        # Only transcription + Gemini analysis raises the score higher.
        # =========================================================
        energy_ai = max(5, min(20, int((rms - 0.008) * 150)))
        fusion_state_early = get_state(session_id)
        video_score_early = fusion_state_early.get("video_score", 0)

        socketio.emit("ai_live_update", {
            "session_id": session_id,
            "status": "speech_detected",
            "ai_percent": energy_ai,
            "human_percent": 100 - energy_ai,
            "is_speaking": True
        })
        socketio.emit("risk_update", {
            "session_id": session_id,
            "video_score": video_score_early,
            "audio_score": energy_ai,
            "final_score": max(energy_ai, video_score_early),
            "violation_level": "low"
        })

        buffer = state["speech_buffer"]

        if len(buffer) < SPEECH_BUFFER_SIZE:
            return

        # ==========================================
        # STEP 1: TRANSCRIPTION
        # ==========================================

        combined_float = np.concatenate(buffer)   # float32 array

        # Convert back to int16 bytes for transcription service
        combined_int16 = (combined_float * 32768.0).clip(-32768, 32767).astype(np.int16)
        combined_bytes = combined_int16.tobytes()

        from app.services.transcription_service import transcribe_audio

        try:
            transcript_result = transcribe_audio(combined_bytes)
        except Exception as te:
            logger.error(f"Transcription crashed (non-fatal): {te}")
            transcript_result = {"text": "[speech detected]", "model": "error-fallback"}

        if isinstance(transcript_result, dict):
            transcript_text = transcript_result.get("text", "")
            transcription_model = transcript_result.get("model", "unknown")
        else:
            transcript_text = str(transcript_result) if transcript_result else ""
            transcription_model = "unknown"

        # Clear buffer regardless
        state["speech_buffer"] = []

        # ==========================================
        # STEP 1b: placeholder / no useful transcript → energy-based score
        # ==========================================
        placeholder_texts = {"[speech detected]", "[transcription in progress...]"}
        is_placeholder = (
            not transcript_text
            or len(transcript_text.strip()) < 10
            or transcript_text.strip().lower() in placeholder_texts
        )

        if is_placeholder:
            logger.info(f"[{session_id}] No/placeholder transcript (rms={rms:.4f}) - speech detected, assuming HUMAN")

            # ============================================================
            # When we detect speech but can't transcribe it,
            # ASSUME HUMAN. Only text analysis should raise AI score.
            # Real human speaking naturally → low AI score (5-15)
            # ============================================================
            ai_score_energy = max(5, min(15, int(rms * 100)))
            human_score_energy = 100 - ai_score_energy

            state["scores"].append(ai_score_energy)
            update_audio(session_id, ai_score_energy)

            now = time.time()
            state["last_emit_time"] = now

            socketio.emit("ai_live_update", {
                "session_id": session_id,
                "status": "speech_detected_no_transcript",
                "ai_percent": ai_score_energy,
                "human_percent": human_score_energy,
                "is_speaking": True,
                "transcript": "[Human speech detected]",
                "detection_source": "energy"
            })

            # Also emit risk_update so video+audio scores both show
            fusion_state = get_state(session_id)
            video_score = fusion_state.get("video_score", 0)
            final_score = max(ai_score_energy, video_score)
            socketio.emit("risk_update", {
                "session_id": session_id,
                "video_score": video_score,
                "audio_score": ai_score_energy,
                "final_score": final_score,
                "violation_level": "low" if ai_score_energy < 30 else "medium"
            })
            return

        # Accumulate full transcript
        state["full_transcript"] += " " + transcript_text

        logger.info(
            f"📝 [{transcription_model}] Transcript: '{transcript_text[:80]}' "
            f"(Total: {len(state['full_transcript'])} chars)"
        )

        # ==============================================
        # STEP 2: AI TEXT DETECTION (Gemini + Heuristic)
        # ==============================================

        from app.services.ai_text_detector import detect_ai_text

        detection_result = detect_ai_text(
            transcript=state["full_transcript"],
            session_id=session_id,
            use_gemini=True
        )

        ai_score = detection_result.get("ai_score", 0)
        human_score = detection_result.get("human_score", 100)
        reasons = detection_result.get("reasons", [])
        verdict = detection_result.get("verdict", "UNCERTAIN")
        source = detection_result.get("source", "unknown")
        confidence = detection_result.get("confidence", 50)
        smoothed_ai = detection_result.get("smoothed_ai_score", ai_score)

        state["scores"].append(smoothed_ai)

        # Store detection in history
        state["detection_history"].append({
            "time": time.strftime("%H:%M:%S"),
            "ai_score": ai_score,
            "verdict": verdict,
            "source": source,
            "transcript_snippet": transcript_text[:100]
        })

        # Use smoothed score for fusion
        update_audio(session_id, smoothed_ai)

        fusion_state = get_state(session_id)
        video_score = fusion_state.get("video_score", 0)
        final_score = max(smoothed_ai, video_score)

        # Determine violation level
        if smoothed_ai >= 70:
            violation_level = "critical"
        elif smoothed_ai >= 50:
            violation_level = "high"
        elif smoothed_ai >= 30:
            violation_level = "medium"
        else:
            violation_level = "low"

        # ==================
        # EMIT UPDATES
        # ==================

        now = time.time()

        if now - state["last_emit_time"] >= EMIT_INTERVAL:

            state["last_emit_time"] = now

            # Live AI detection update
            socketio.emit("ai_live_update", {
                "session_id": session_id,
                "ai_percent": smoothed_ai,
                "human_percent": 100 - smoothed_ai,
                "is_speaking": True,
                "transcript": transcript_text[:100],
                "detection_source": source,
                "verdict": verdict,
                "transcription_model": transcription_model
            })

            # Risk score update
            socketio.emit("risk_update", {
                "session_id": session_id,
                "video_score": video_score,
                "audio_score": smoothed_ai,
                "final_score": final_score,
                "violation_level": violation_level
            })

            # Fraud alert (with detailed AI detection info)
            socketio.emit("fraud_alert", {
                "session_id": session_id,
                "video_score": video_score,
                "audio_score": smoothed_ai,
                "final_score": final_score,
                "violation_level": violation_level,
                "reasons": reasons[:5],
                "transcript": transcript_text[:200],
                "time": time.strftime("%H:%M:%S"),
                "confidence": confidence,
                "ai_detection": {
                    "source": source,
                    "verdict": verdict,
                    "gemini_score": detection_result.get("gemini_score"),
                    "heuristic_score": detection_result.get("heuristic_score")
                }
            })

    except Exception as e:
        logger.error(f"Audio chunk handler error: {e}", exc_info=True)


# ================================================
# SOCKET EVENT HANDLERS
# ================================================

@socketio.on("disconnect")
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")