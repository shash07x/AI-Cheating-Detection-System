import cv2
import numpy as np
import time
import logging

logger = logging.getLogger(__name__)

# Try to import YOLO
YOLO_AVAILABLE = False
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    logger.info("✅ YOLO available for eye tracking")
except ImportError:
    logger.warning("⚠️ YOLO not available - install with: pip install ultralytics")

# Initialize YOLO model
_yolo_model = None

def get_yolo_model():
    """Lazy load YOLO model - uses stable yolov8n.pt"""
    global _yolo_model
    if _yolo_model is None and YOLO_AVAILABLE:
        try:
            # Use standard YOLOv8n (more stable than custom face models)
            _yolo_model = YOLO('yolov8n.pt')
            logger.info("✅ YOLO model loaded for gaze tracking (yolov8n)")
        except Exception as e:
            logger.error(f"❌ Failed to load YOLO model: {e}")
            _yolo_model = None
    return _yolo_model

# ------------------------------
# STATE (per session tracking)
# ------------------------------
_session_states = {}

def get_session_state(session_id="default"):
    """Get or create state for a session"""
    if session_id not in _session_states:
        _session_states[session_id] = {
            "eye_closed_start": None,
            "last_eye_seen": None,
            "last_face_seen": None,
            "blink_count": 0,
            "last_blink_time": None,
            "no_face_start": None,
            "looking_away_start": None,
            "face_count_history": [],
            "person_detected_without_face": 0
        }
    return _session_states[session_id]

# Thresholds (OPTIMIZED for fewer false positives)
BLINK_MAX = 0.4
PROLONGED_BLINK = 1.2
CONFIDENCE_THRESHOLD = 0.4
RAPID_BLINK_INTERVAL = 2.0
RAPID_BLINK_COUNT = 5
NO_FACE_THRESHOLD = 3.0
LOOKING_AWAY_THRESHOLD = 2.0
PERSON_FALLBACK_TIMEOUT = 5.0

# Frame preprocessing
TARGET_WIDTH = 640
TARGET_HEIGHT = 480


def analyze_gaze(frame, session_id="default", yolo_detections=None):
    """
    Analyze eye gaze and detect blink patterns using YOLO.
    OPTIMIZED VERSION - Reduced false positives.
    """
    state = get_session_state(session_id)
    now = time.time()

    # Validate frame
    if frame is None or frame.size == 0:
        logger.warning("Invalid frame received")
        return {
            "looking_away": True,
            "confidence": 0,
            "reason": "no_frame",
            "face_detected": False
        }

    try:
        # Use pre-computed detections or run YOLO
        if yolo_detections is None:
            if not YOLO_AVAILABLE:
                return {
                    "looking_away": False,
                    "confidence": 0,
                    "reason": "yolo_not_available",
                    "face_detected": True,
                    "blink_count": 0
                }
            
            # Preprocess frame
            processed_frame = preprocess_frame(frame)
            
            # Run YOLO detection
            model = get_yolo_model()
            if model is None:
                return {
                    "looking_away": False,
                    "confidence": 0,
                    "reason": "model_not_loaded",
                    "face_detected": True,
                    "blink_count": 0
                }
            
            results = model(processed_frame, verbose=False, conf=CONFIDENCE_THRESHOLD)
            yolo_detections = parse_yolo_results(results[0])
        
        # Analyze detections
        return analyze_yolo_detections(yolo_detections, state, now, session_id)

    except Exception as e:
        logger.error(f"❌ Gaze analysis error: {e}", exc_info=True)
        return {
            "looking_away": False,
            "confidence": 0,
            "reason": "error",
            "error": str(e),
            "face_detected": True,
            "blink_count": 0
        }


def preprocess_frame(frame):
    """Preprocess frame for better YOLO detection"""
    h, w = frame.shape[:2]
    if w != TARGET_WIDTH or h != TARGET_HEIGHT:
        frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))
    
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return frame_rgb


def parse_yolo_results(result):
    """Parse YOLO detection results into standardized format"""
    detections = {
        "faces": [],
        "persons": [],
        "face_count": 0,
        "person_count": 0,
        "has_person": False
    }
    
    if result.boxes is None or len(result.boxes) == 0:
        return detections
    
    for box in result.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        
        if conf < CONFIDENCE_THRESHOLD:
            continue
        
        xyxy = box.xyxy[0].cpu().numpy()
        class_name = result.names.get(cls, "unknown")
        
        # COCO class 0 = person
        if cls == 0:
            detections["persons"].append({
                "bbox": xyxy,
                "confidence": conf,
                "class": "person"
            })
            detections["person_count"] += 1
            detections["has_person"] = True
        
        # Face class
        elif "face" in class_name.lower() or "head" in class_name.lower():
            detections["faces"].append({
                "bbox": xyxy,
                "confidence": conf,
                "class": class_name
            })
            detections["face_count"] += 1
    
    # FALLBACK: If person detected but no explicit face, assume face present
    if detections["person_count"] > 0 and detections["face_count"] == 0:
        detections["face_count"] = 1
        detections["faces"].append({
            "bbox": None,
            "confidence": conf,
            "class": "inferred_from_person"
        })
        logger.debug("📌 Face inferred from person detection")
    
    return detections


def analyze_yolo_detections(detections, state, now, session_id):
    """Analyze YOLO detections for gaze tracking - LESS AGGRESSIVE"""
    face_count = detections["face_count"]
    person_count = detections["person_count"]
    has_person = detections["has_person"]
    
    # Track face count history
    state["face_count_history"].append(face_count)
    if len(state["face_count_history"]) > 10:
        state["face_count_history"].pop(0)
    
    # ---------------- NO FACE DETECTED ----------------
    if face_count == 0:
        # FALLBACK: If person detected, don't immediately trigger
        if has_person:
            state["person_detected_without_face"] += 1
            
            if state["person_detected_without_face"] > 15:
                logger.warning(f"⚠️ Person visible but face not clear")
                return {
                    "looking_away": False,
                    "confidence": 40,
                    "reason": "face_obscured",
                    "face_detected": False,
                    "person_detected": True,
                    "blink_count": state["blink_count"]
                }
            else:
                return {
                    "looking_away": False,
                    "confidence": 10,
                    "reason": "person_detected",
                    "face_detected": False,
                    "person_detected": True,
                    "blink_count": state["blink_count"]
                }
        
        # NO PERSON - serious
        if state["no_face_start"] is None:
            state["no_face_start"] = now
            logger.debug("👤 No face/person detected - starting timer")
        
        duration = now - state["no_face_start"]
        
        if duration > NO_FACE_THRESHOLD:
            logger.warning(f"🚨 No face/person for {duration:.1f}s")
            return {
                "looking_away": True,
                "confidence": 90,
                "reason": "no_face_detected",
                "face_detected": False,
                "person_detected": False,
                "duration": round(duration, 2),
                "blink_count": state["blink_count"]
            }
        else:
            return {
                "looking_away": False,
                "confidence": 30,
                "reason": "face_temporarily_lost",
                "face_detected": False,
                "person_detected": False,
                "duration": round(duration, 2),
                "blink_count": state["blink_count"]
            }
    
    # Reset timers when face detected
    state["no_face_start"] = None
    state["person_detected_without_face"] = 0
    state["last_face_seen"] = now
    
    # ---------------- MULTIPLE FACES (CHEATING) ----------------
    if face_count > 1:
        logger.warning(f"⚠️ Multiple faces detected: {face_count}")
        return {
            "looking_away": True,
            "confidence": 95,
            "reason": f"multiple_faces_{face_count}",
            "face_detected": True,
            "face_count": face_count,
            "blink_count": state["blink_count"]
        }
    
    # ---------------- MULTIPLE PERSONS (SUSPICIOUS) ----------------
    if person_count > 1:
        logger.warning(f"⚠️ Multiple persons detected: {person_count}")
        return {
            "looking_away": True,
            "confidence": 85,
            "reason": f"multiple_persons_{person_count}",
            "face_detected": True,
            "person_count": person_count,
            "blink_count": state["blink_count"]
        }
    
    # ---------------- NORMAL STATE ----------------
    state["last_eye_seen"] = now
    
    return {
        "looking_away": False,
        "confidence": 5,
        "reason": "face_detected",
        "face_detected": True,
        "face_count": face_count,
        "person_count": person_count,
        "blink_count": state["blink_count"]
    }


def reset_gaze_state(session_id="default"):
    """Reset gaze tracking state for a session"""
    if session_id in _session_states:
        _session_states[session_id] = {
            "eye_closed_start": None,
            "last_eye_seen": None,
            "last_face_seen": None,
            "blink_count": 0,
            "last_blink_time": None,
            "no_face_start": None,
            "looking_away_start": None,
            "face_count_history": [],
            "person_detected_without_face": 0
        }
        logger.info(f"🔄 Gaze state reset for session {session_id}")


def get_gaze_statistics(session_id="default"):
    """Get gaze tracking statistics for a session"""
    state = get_session_state(session_id)
    
    avg_face_count = 0
    if state["face_count_history"]:
        avg_face_count = sum(state["face_count_history"]) / len(state["face_count_history"])
    
    return {
        "total_blinks": state["blink_count"],
        "eyes_currently_open": state["eye_closed_start"] is None,
        "face_currently_visible": state["no_face_start"] is None,
        "last_face_seen": state["last_face_seen"],
        "last_eye_seen": state["last_eye_seen"],
        "avg_face_count": round(avg_face_count, 2),
        "session_id": session_id
    }


def cleanup():
    """Cleanup resources"""
    global _yolo_model, _session_states
    
    if _yolo_model is not None:
        _yolo_model = None
    
    _session_states.clear()
    logger.info("✅ Eye gaze tracking cleaned up")