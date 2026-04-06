"""
Fallback head pose estimation using cascade classifiers (no YOLO required)
"""

import cv2
import numpy as np
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Cascade files
FACE_CASCADE = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(FACE_CASCADE)

_frame_count = 0
_last_analysis_time = 0


def estimate_head_pose_fallback(frame: np.ndarray) -> Dict:
    """
    Fallback head pose estimation using cascade classifier when YOLO fails.
    Provides basic face detection and head position tracking.
    """
    global _frame_count, _last_analysis_time
    _frame_count += 1
    
    now = time.time()
    
    try:
        h, w, _ = frame.shape
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        person_count = len(faces)
        logger.debug(f"🔍 Detected {person_count} face(s) using cascade")
        
        # ===== CRITICAL: Multiple faces =====
        if person_count > 1:
            logger.warning(f"🚨 CRITICAL: {person_count} faces detected (cascade)")
            return {
                "status": "normal",
                "looking_away": False,
                "direction": "center",
                "confidence": 80,
                "severity": "high",
                "eyes_closed": False,
                "offset_horizontal": 0.0,
                "offset_vertical": 0.0,
                "phone_detected": False,
                "multiple_faces": True,
                "person_count": person_count,
                "face_id": None,
                "face_changed": False,
                "fps": 0,
                "timestamp": now,
                "frame_number": _frame_count
            }
        
        # ===== No face detected =====
        if person_count == 0:
            logger.warning(f"⚠️ NO FACE DETECTED (cascade)")
            return {
                "status": "no_face",
                "looking_away": True,
                "severity": "high",
                "phone_detected": False,
                "multiple_faces": False,
                "person_count": 0,
                "face_id": None,
                "face_changed": False,
                "timestamp": now,
                "frame_number": _frame_count
            }
        
        # ===== One face detected: analyze position =====
        x, y, fw, fh = faces[0]
        face_center_x = x + fw / 2
        face_center_y = y + fh / 2
        
        # Calculate offsets from image center
        offset_x = abs(face_center_x - w / 2) / w
        offset_y = abs(face_center_y - h / 2) / h
        
        # Determine direction
        direction = "center"
        looking_away = False
        
        if offset_x > 0.2:  # Head turned left/right
            looking_away = True
            direction = "left" if face_center_x < w / 2 else "right"
            logger.debug(f"👀 Head turned {direction} (offset_x={offset_x:.2f})")
        
        elif offset_y > 0.25:  # Head tilted up/down
            looking_away = True
            direction = "down" if face_center_y > h / 2 else "up"
            logger.debug(f"👀 Head tilted {direction} (offset_y={offset_y:.2f})")
        
        logger.debug(
            f"📊 Face: center=({face_center_x:.0f}, {face_center_y:.0f}), "
            f"offsets=({offset_x:.2f}, {offset_y:.2f}), away={looking_away}"
        )
        
        return {
            "status": "sustained_away" if looking_away else "normal",
            "looking_away": looking_away,
            "direction": direction,
            "confidence": 70,
            "severity": "medium" if looking_away else "none",
            "eyes_closed": False,
            "offset_horizontal": round(offset_x, 4),
            "offset_vertical": round(offset_y, 4),
            "phone_detected": False,
            "multiple_faces": False,
            "person_count": 1,
            "face_id": None,
            "face_changed": False,
            "fps": 0,
            "timestamp": now,
            "frame_number": _frame_count
        }
    
    except Exception as e:
        logger.error(f"❌ Cascade error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "looking_away": False,
            "severity": "medium"
        }


if __name__ == "__main__":
    # Test the fallback
    print("Testing fallback head pose detection...")
    
    # Create a test frame (blank)
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = estimate_head_pose_fallback(test_frame)
    
    print(f"Result: {result}")
    print(f"✅ Fallback working (should show 'no_face' for blank frame)")
