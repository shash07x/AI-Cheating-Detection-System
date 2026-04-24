from flask import Blueprint, jsonify, request
import base64
import cv2
import numpy as np
import logging
import os
import time

from app.services.eye_gaze_tracking import analyze_gaze, reset_gaze_state
from app.services.head_pose_estimation import estimate_head_pose, get_statistics, reset_state
from app.services.head_pose_fallback import estimate_head_pose_fallback
from app.services.stable_vision_engine import analyze_frame, HeadPose, reset_session as reset_vision_session
from app.services.fusion_state import update_video, get_state, record_event_in_state
from app.services.final_report_engine import record_event
from app.extensions import socketio

logger = logging.getLogger(__name__)

video_bp = Blueprint("video", __name__, url_prefix="/video")

# Configuration
BLACK_FRAME_THRESHOLD = 10
COVERED_FRAME_VARIANCE = 15
EVIDENCE_BASE_DIR = "evidence"
EVIDENCE_COOLDOWN = 2

os.makedirs(EVIDENCE_BASE_DIR, exist_ok=True)

LAST_EVIDENCE_TIME = {}
FRAME_COUNT = {}


def sanitize(data):
    from collections import deque
    if isinstance(data, dict):
        return {k: sanitize(v) for k, v in data.items()}
    elif isinstance(data, (list, deque)):
        return [sanitize(v) for v in data]
    elif isinstance(data, (np.bool_, bool)):
        return bool(data)
    elif isinstance(data, (np.integer, int)):
        return int(data)
    elif isinstance(data, (np.floating, float)):
        return float(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    elif data is None:
        return None
    else:
        return data


def save_evidence(session_id, frame, prefix):

    now = time.time()

    if session_id in LAST_EVIDENCE_TIME:
        if now - LAST_EVIDENCE_TIME[session_id] < EVIDENCE_COOLDOWN:
            return None

    LAST_EVIDENCE_TIME[session_id] = now

    session_dir = os.path.join(EVIDENCE_BASE_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    filename = f"{prefix}_{int(now)}.jpg"
    path = os.path.join(session_dir, filename)

    try:
        cv2.imwrite(path, frame)
        relative_path = f"evidence/{session_id}/{filename}"
        logger.info(f"💾 Saved evidence: {relative_path}")
        return relative_path
    except Exception as e:
        logger.error(f"Save evidence error: {e}")
        return None


@video_bp.route("/analyze", methods=["POST", "OPTIONS"])
def analyze_video():

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:

        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "No data"}), 400

        session_id = data.get("session_id", "session_01")
        frame_b64 = data.get("frame")

        if not frame_b64:
            return jsonify({"error": "No frame"}), 400

        if session_id not in FRAME_COUNT:
            FRAME_COUNT[session_id] = 0

        FRAME_COUNT[session_id] += 1

        logger.info(f"🎥 Frame {FRAME_COUNT[session_id]} - Analyzing for session {session_id}")

        try:

            if ',' in frame_b64:
                frame_b64 = frame_b64.split(',')[1]

            img_bytes = base64.b64decode(frame_b64)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame.mean() < 1:
                logger.warning("Fully black frame - likely camera blocked")
                # Don't return early - let it flow to camera-blocked detection

            frame = cv2.resize(frame, (960, 720))

            if frame is None:
                return jsonify({"error": "Invalid frame"}), 400

        except Exception as e:
            logger.error(f"Frame decode error: {e}")
            return jsonify({"error": "Decode failed"}), 400

        violation_level = "low"
        video_score = 10
        reasons = []
        evidence_path = None
        detection_type = "normal"

        logger.debug(f"Starting video analysis for session {session_id}")

        # ===== Step 1: Check for camera obstruction =====
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        brightness_variance = np.var(gray)

        logger.debug(f"Brightness: {mean_brightness:.2f}, Variance: {brightness_variance:.2f}")

        if mean_brightness < BLACK_FRAME_THRESHOLD or brightness_variance < COVERED_FRAME_VARIANCE:
            violation_level = "critical"
            video_score = 95
            reasons.append("🚨 Camera blocked/covered")
            evidence_path = save_evidence(session_id, frame, "blocked")
            detection_type = "camera_blocked"
            record_event(session_id, "camera")
            record_event_in_state(session_id, "camera")
        else:
            # ===== Step 2: Run head pose detection =====
            try:
                from app.extensions import global_pytorch_lock
                acquired = global_pytorch_lock.acquire(timeout=10)
                if not acquired:
                    logger.warning("⚠️ Could not acquire pytorch lock for YOLO (Whisper busy)")
                    head_pose_result = estimate_head_pose_fallback(frame)
                else:
                    try:
                        head_pose_result = estimate_head_pose(frame)
                    finally:
                        global_pytorch_lock.release()
                
                # Check if YOLO failed (returned error status), use fallback
                if head_pose_result.get("status") == "error":
                    logger.warning(f"⚠️ YOLO error: {head_pose_result.get('error')}, using fallback cascade")
                    head_pose_result = estimate_head_pose_fallback(frame)
                
                logger.debug(f"📍 Head Pose Result: {head_pose_result}")
                logger.debug(f"   - Status: {head_pose_result.get('status')}")
                logger.debug(f"   - Phone Detected: {head_pose_result.get('phone_detected')}")
                logger.debug(f"   - Multiple Faces: {head_pose_result.get('multiple_faces')}")
                logger.debug(f"   - Face Changed: {head_pose_result.get('face_changed')}")
                
                # ===== CRITICAL ALERTS =====
                # Check for phone detection
                if head_pose_result.get("phone_detected"):
                    logger.warning(f"🚨 CRITICAL ALERT: PHONE DETECTED")
                    violation_level = "critical"
                    video_score = 90
                    reasons.append("📱 PHONE DETECTED IN FRAME")
                    evidence_path = save_evidence(session_id, frame, "phone_detected")
                    detection_type = "phone_detected"
                    record_event(session_id, "phone")
                    record_event_in_state(session_id, "phone")
                
                # Check for multiple faces
                elif head_pose_result.get("multiple_faces"):
                    logger.warning(f"🚨 CRITICAL ALERT: MULTIPLE FACES")
                    person_count = head_pose_result.get("person_count", 2)
                    violation_level = "critical"
                    video_score = 95
                    reasons.append(f"👥 MULTIPLE FACES DETECTED ({person_count})")
                    evidence_path = save_evidence(session_id, frame, "multiple_faces")
                    detection_type = f"multiple_faces_{person_count}"
                    record_event(session_id, "multiple_person")
                    record_event_in_state(session_id, "multiple_person")
                
                # Check for face change (impersonation)
                elif head_pose_result.get("face_changed"):
                    logger.warning(f"🚨 CRITICAL ALERT: FACE CHANGED")
                    violation_level = "critical"
                    video_score = 99
                    reasons.append("🔄 FACE CHANGED - Possible impersonation")
                    evidence_path = save_evidence(session_id, frame, "face_swap")
                    detection_type = "face_changed"
                    record_event(session_id, "multiple_person")
                    record_event_in_state(session_id, "multiple_person")
                
                # Check for no face
                elif head_pose_result.get("status") == "no_face":
                    logger.warning(f"⚠️ MEDIUM ALERT: NO FACE")
                    violation_level = "medium"
                    video_score = 60
                    reasons.append("❌ NO FACE DETECTED")
                    evidence_path = save_evidence(session_id, frame, "no_face")
                    detection_type = "no_face"
                    record_event(session_id, "looking_away")
                    record_event_in_state(session_id, "looking_away")
                
                else:
                    logger.debug(f"📝 Normal status detected, calling SVE analysis")
                    # ===== Convert head pose result to HeadPose object =====
                    head_pose = None
                    if head_pose_result.get("status") in ["normal", "sustained_away"]:
                        head_pose = HeadPose(
                            direction=head_pose_result.get("direction", "center"),
                            horizontal_offset=float(head_pose_result.get("offset_horizontal", 0)),
                            vertical_offset=float(head_pose_result.get("offset_vertical", 0)),
                            eyes_closed=head_pose_result.get("eyes_closed", False),
                        )
                        logger.debug(f"   HeadPose: dir={head_pose.direction}, h_offset={head_pose.horizontal_offset}, v_offset={head_pose.vertical_offset}")
                    
                    # ===== Run SVE (Stable Vision Engine) analysis =====
                    face_count = head_pose_result.get("person_count", 1)
                    phone_detected = head_pose_result.get("phone_detected", False)
                    
                    logger.debug(f"   Calling analyze_frame: face_count={face_count}, phone_detected={phone_detected}")
                    
                    sve_analysis = analyze_frame(
                        frame=frame,
                        head_pose=head_pose,
                        face_count=face_count,
                        phone_detected=phone_detected,
                        session_id=session_id
                    )
                    
                    logger.debug(f"   SVE returned: alert_level={sve_analysis.alert_level}, score={sve_analysis.score}, type={sve_analysis.detection_type}")
                    
                    # ===== Map SVE results to violation level =====
                    # alert_level is already a string (e.g., "critical", "medium", "low", "none")
                    violation_level = sve_analysis.alert_level
                    if violation_level == "none":
                        violation_level = "low"
                    
                    video_score = sve_analysis.score
                    detection_type = sve_analysis.detection_type
                    reasons.append(sve_analysis.reason)
                    
                    # Save screenshot if SVE detected critical/medium with screenshot flag
                    if sve_analysis.screenshot_taken and sve_analysis.screenshot_path:
                        evidence_path = sve_analysis.screenshot_path
                    
                    logger.info(
                        f"🎬 SVE Analysis: {sve_analysis.detection_type} | "
                        f"Alert: {violation_level} | Score: {sve_analysis.score}"
                    )
            
            except Exception as e:
                logger.error(f"❌ Vision analysis error: {e}", exc_info=True)
                violation_level = "low"
                video_score = 10
                reasons.append("⚠️ Vision analysis error")
                detection_type = "analysis_error"

        update_video(session_id, video_score)
        state = get_state(session_id)

        audio_score = state.get("audio_score", 0)
        final_score = max(video_score, audio_score)

        # violation_level is now guaranteed to be a string (critical, medium, low)
        violation_level_str = violation_level

        # Map confidence based on violation level
        if violation_level_str == "critical":
            confidence = 95
        elif violation_level_str == "medium":
            confidence = 75
        else:
            confidence = 50

        logger.info(f"📊 RESULT: Level={violation_level_str}, Score={video_score}, Type={detection_type}, Reason={reasons}")

        risk_payload = {
            "session_id": session_id,
            "video_score": video_score,
            "audio_score": audio_score,
            "final_score": final_score,
            "violation_level": violation_level_str
        }

        logger.debug(f"📡 Emitting risk_update: {risk_payload}")
        socketio.emit("risk_update", risk_payload)

        alert_payload = {
            "session_id": session_id,
            "video_score": video_score,
            "audio_score": audio_score,
            "final_score": final_score,
            "violation_level": violation_level_str,
            "detection_type": detection_type,
            "reasons": reasons,
            "confidence": confidence,
            "time": time.strftime("%H:%M:%S"),
            "frame_number": FRAME_COUNT[session_id]
        }

        if evidence_path is not None:
            alert_payload["evidence"] = evidence_path

        logger.info(f"🚨 Emitting fraud_alert: Level={violation_level_str}, Score={video_score}, Type={detection_type}")
        logger.debug(f"   Payload: {alert_payload}")
        socketio.emit("fraud_alert", alert_payload)

        return jsonify({
            "status": "ok",
            "video_score": video_score,
            "final_score": final_score,
            "violation_level": violation_level,
            "frame_count": FRAME_COUNT[session_id]
        })

    except Exception as e:
        logger.error(f"❌ Video analysis error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@video_bp.route("/reset/<session_id>", methods=["POST"])
def reset_session(session_id):

    try:
        reset_state()
        reset_gaze_state(session_id)
        reset_vision_session(session_id)

        if session_id in FRAME_COUNT:
            FRAME_COUNT[session_id] = 0

        return jsonify({"status": "reset", "session_id": session_id})

    except Exception as e:
        logger.error(f"Reset error: {e}")
        return jsonify({"error": str(e)}), 500


@video_bp.route("/statistics/<session_id>", methods=["GET"])
def stats(session_id):

    try:

        from app.services.eye_gaze_tracking import get_gaze_statistics

        stats_data = {
            "session_id": session_id,
            "frame_count": FRAME_COUNT.get(session_id, 0),
            "head_pose": get_statistics(),
            "gaze": get_gaze_statistics(session_id),
            "fusion": get_state(session_id)
        }

        return jsonify(sanitize(stats_data))

    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({"error": str(e)}), 500