import cv2
import numpy as np
import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
from app.services.yolo_loader import load_yolo_safe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proctoring.face_id")

# ================= CONFIG =================

@dataclass
class HeadPoseConfig:
    HORIZONTAL_THRESHOLD: float = 0.15
    VERTICAL_THRESHOLD: float = 0.20
    EYE_CLOSE_THRESHOLD: float = 5.0
    YOLO_CONF_THRESHOLD: float = 0.5   # NEW: confidence filter

config = HeadPoseConfig()

# ================= ENUMS =================

class Direction(Enum):
    CENTER = "center"
    LEFT = "left"
    RIGHT = "right"
    DOWN = "down"

class Severity(Enum):
    NONE = "none"
    MEDIUM = "medium"
    HIGH = "high"

class Status(Enum):
    NORMAL = "normal"
    NO_FACE = "no_face"
    SUSTAINED_AWAY = "sustained_away"
    ERROR = "error"

# ================= YOLO =================

_model = None       # Pose model (keypoints + person tracking)
_det_model = None   # Detection model (phone, objects)
_last_face_id = None
_frame_count = 0
_first_frame = True


def initialize_model():
    global _model
    if _model is None:
        logger.info("Loading YOLOv8 Pose model...")
        _model = load_yolo_safe("yolov8n-pose.pt")
        logger.info("YOLO Pose model loaded")
    return _model


def initialize_det_model():
    global _det_model
    if _det_model is None:
        logger.info("Loading YOLOv8 Detection model (for phone detection)...")
        _det_model = load_yolo_safe("yolov8n.pt")
        if _det_model:
            logger.info(f"YOLO Det model loaded - classes: {list(_det_model.names.values())[:10]}...")
    return _det_model


def reset_state():
    global _frame_count, _last_face_id
    _frame_count = 0
    _last_face_id = None


# ================= HELPERS =================

def dist(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))


# ================= MAIN =================

def estimate_head_pose(frame: Optional[np.ndarray] = None) -> Dict:

    logger.info("🤖 YOLO FUNCTION ENTERED")

    global _frame_count, _last_face_id, _first_frame
    _frame_count += 1

    now = time.time()
    start = time.perf_counter()

    if frame is None:
        return {"status": "no_frame"}

    try:

        model = initialize_model()

        if model is None:
            raise RuntimeError("YOLO model unavailable")

        h, w, _ = frame.shape

        logger.info(f"📸 YOLO processing frame {_frame_count}")

        results = model.track(frame, persist=True, verbose=False)[0]

        if _first_frame:
            logger.info("🚀 FIRST YOLO FRAME PROCESSED SUCCESSFULLY")
            _first_frame = False

        phone_detected = False
        persons = []
        face_id = None

        # ---------- POSE MODEL LOOP (persons + keypoints) ----------
        for box in results.boxes:

            conf = float(box.conf[0])  # detection confidence

            if conf < config.YOLO_CONF_THRESHOLD:
                continue

            cls = int(box.cls[0])
            label = model.names[cls]

            if label == "person":
                persons.append(box)

        person_count = len(persons)
        multiple_faces = person_count > 1

        # ---------- PHONE DETECTION (separate model) ----------
        # yolov8n-pose.pt only has 'person' class, so we use yolov8n.pt
        # which has 80 COCO classes including 'cell phone' (class 67)
        try:
            det_model = initialize_det_model()
            if det_model is not None:
                det_results = det_model(frame, verbose=False)[0]
                for box in det_results.boxes:
                    conf = float(box.conf[0])
                    if conf < 0.35:  # Lower threshold for phone detection
                        continue
                    cls = int(box.cls[0])
                    label = det_model.names[cls]
                    if label == "cell phone":
                        phone_detected = True
                        logger.warning(f"📱 PHONE DETECTED! (conf={conf:.2f})")
                    elif label == "laptop":
                        logger.info(f"💻 Laptop detected (conf={conf:.2f})")
                    elif label == "book":
                        logger.info(f"📖 Book detected (conf={conf:.2f})")
        except Exception as det_err:
            logger.warning(f"Phone detection pass failed: {det_err}")

        # ---------- FACE TRACK ID ----------
        if results.boxes.id is not None and len(results.boxes.id) > 0:
            face_id = int(results.boxes.id[0])

        face_changed = False

        if face_id is not None:

            if _last_face_id is None:
                _last_face_id = face_id
                logger.info(f"🧠 Initial Face ID = {face_id}")

            elif face_id != _last_face_id:
                face_changed = True
                logger.warning(f"🚨 FACE CHANGED {_last_face_id} → {face_id}")
                _last_face_id = face_id

        # ---------- KEYPOINTS ----------
        if results.keypoints is None or len(results.keypoints.xy) == 0:

            return {
                "status": Status.NO_FACE.value,
                "looking_away": True,
                "severity": Severity.HIGH.value,
                "phone_detected": phone_detected,
                "multiple_faces": multiple_faces,
                "person_count": person_count,
                "face_id": face_id,
                "face_changed": face_changed
            }

        kps = results.keypoints.xy[0].cpu().numpy()

        nose, le, re = kps[0], kps[1], kps[2]

        cx, cy = nose

        off_x = abs(cx - w / 2) / w
        off_y = abs(cy - h / 2) / h

        direction = Direction.CENTER.value

        if off_x > config.HORIZONTAL_THRESHOLD:
            direction = Direction.LEFT.value if cx < w / 2 else Direction.RIGHT.value

        elif off_y > config.VERTICAL_THRESHOLD:
            direction = Direction.DOWN.value

        eye_gap = dist(le, re)

        eyes_closed = eye_gap < config.EYE_CLOSE_THRESHOLD

        looking_away = (
            off_x > config.HORIZONTAL_THRESHOLD
            or off_y > config.VERTICAL_THRESHOLD
            or eyes_closed
        )

        confidence = 5
        severity = Severity.NONE.value

        if eyes_closed:
            confidence = 85
            severity = Severity.HIGH.value

        elif looking_away:
            confidence = 60
            severity = Severity.MEDIUM.value

        fps = 1 / (time.perf_counter() - start)

        logger.info(
            f"🧠 FaceID={face_id} | persons={person_count} | phone={phone_detected} | "
            f"away={looking_away} | fps={fps:.2f}"
        )

        return {

            "status": Status.SUSTAINED_AWAY.value if looking_away else Status.NORMAL.value,
            "looking_away": looking_away,
            "direction": direction,
            "confidence": confidence,
            "severity": severity,
            "eyes_closed": eyes_closed,

            "offset_horizontal": round(off_x, 4),
            "offset_vertical": round(off_y, 4),

            "phone_detected": phone_detected,
            "multiple_faces": multiple_faces,
            "person_count": person_count,

            "face_id": face_id,
            "face_changed": face_changed,

            "fps": round(fps, 2),
            "timestamp": now,
            "frame_number": _frame_count
        }

    except Exception as e:

        logger.error(f"❌ YOLO ERROR: {e}")

        return {
            "status": "error",
            "error": str(e),
            "looking_away": False,
            "severity": "medium",
            "phone_detected": False,
            "multiple_faces": False,
            "person_count": 0,
            "face_id": None,
            "face_changed": False
        }


# ================= STATS =================

def get_statistics() -> Dict:
    return {
        "frames": _frame_count
    }