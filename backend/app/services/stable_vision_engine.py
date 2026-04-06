"""
Stable Vision Engine (SVE) - Comprehensive Face Analysis System

Detects and responds to:
1. Eye movements (looking at camera - LOW alert)
2. Looking away > 10 seconds (MEDIUM alert + screenshots)
3. Looking away < 10 seconds (MEDIUM alert)
4. Head pose changes (MEDIUM alert + screenshots)
5. Multiple faces (CRITICAL alert + screenshot)
6. Mobile phone detection (CRITICAL alert + screenshot)
"""

import cv2
import numpy as np
import time
import logging
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


# ========== ENUMS ==========

class AlertLevel(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    CRITICAL = "critical"
    NONE = "none"


class DetectionType(Enum):
    """Types of detections"""
    EYES_ON_CAMERA = "eyes_on_camera"
    LOOKING_AWAY_SHORT = "looking_away_short"  # < 10 seconds
    LOOKING_AWAY_LONG = "looking_away_long"    # > 10 seconds
    HEAD_POSE_CHANGE = "head_pose_change"
    MULTIPLE_FACES = "multiple_faces"
    PHONE_DETECTED = "phone_detected"
    NORMAL = "normal"


# ========== DATA CLASSES ==========

@dataclass
class HeadPose:
    """Head pose information"""
    direction: str  # "center", "left", "right", "up", "down"
    horizontal_offset: float  # -1 to 1 (negative=left, positive=right)
    vertical_offset: float    # -1 to 1 (negative=up, positive=down)
    eyes_closed: bool = False
    
    def is_normal(self, h_threshold=0.15, v_threshold=0.20):
        """Check if head pose is normal"""
        return (abs(self.horizontal_offset) < h_threshold and 
                abs(self.vertical_offset) < v_threshold and 
                not self.eyes_closed)


@dataclass
class VisionAnalysis:
    """Complete vision analysis result"""
    timestamp: float
    detection_type: str
    alert_level: str
    confidence: float
    score: float  # 0-100, higher = more suspicious
    reason: str
    
    # Detection details
    face_count: int = 1
    phone_detected: bool = False
    eyes_closed: bool = False
    head_pose: Optional[Dict] = None
    looking_away_duration: Optional[float] = None
    
    # Actions
    screenshot_taken: bool = False
    screenshot_path: Optional[str] = None
    
    def to_dict(self):
        d = asdict(self)
        d['timestamp'] = round(d['timestamp'], 2)
        if d['looking_away_duration']:
            d['looking_away_duration'] = round(d['looking_away_duration'], 2)
        return d


# ========== SESSION STATE ==========

@dataclass
class SessionState:
    """Per-session tracking state"""
    session_id: str
    
    # Looking away tracking
    looking_away_start: Optional[float] = None
    last_looking_away_alert: Optional[float] = None
    
    # Head pose tracking
    last_head_pose: Optional[HeadPose] = None
    head_pose_changed_time: Optional[float] = None
    
    # Face tracking
    last_face_count: int = 1
    multiple_faces_detected_time: Optional[float] = None
    
    # Phone detection
    phone_detected_start: Optional[float] = None
    
    # General
    last_analysis: Optional[VisionAnalysis] = None
    frame_count: int = 0
    

_session_states: Dict[str, SessionState] = {}


def get_session_state(session_id: str) -> SessionState:
    """Get or create session state"""
    if session_id not in _session_states:
        _session_states[session_id] = SessionState(session_id=session_id)
    return _session_states[session_id]


# ========== CONFIGURATION ==========

class SVEConfig:
    """Stable Vision Engine Configuration"""
    
    # Thresholds
    LOOKING_AWAY_SHORT_THRESHOLD = 10.0  # seconds (< 10s)
    LOOKING_AWAY_LONG_THRESHOLD = 10.0   # seconds (> 10s)
    
    HEAD_POSE_H_THRESHOLD = 0.15  # horizontal deviation
    HEAD_POSE_V_THRESHOLD = 0.20  # vertical deviation
    
    EYES_CLOSED_THRESHOLD = 5.0   # pixel distance
    
    # Alert cooldowns (prevent alert spam)
    LOOKING_AWAY_ALERT_COOLDOWN = 5.0  # seconds
    PHONE_ALERT_COOLDOWN = 30.0        # seconds
    
    # Screenshot settings
    SCREENSHOT_DIR = "backend/evidence"
    TAKE_SCREENSHOT_ON = {
        DetectionType.LOOKING_AWAY_LONG.value,
        DetectionType.HEAD_POSE_CHANGE.value,
        DetectionType.MULTIPLE_FACES.value,
        DetectionType.PHONE_DETECTED.value,
    }


# ========== ANALYSIS FUNCTIONS ==========

def analyze_frame(
    frame: np.ndarray,
    head_pose: Optional[HeadPose],
    face_count: int = 1,
    phone_detected: bool = False,
    session_id: str = "default"
) -> VisionAnalysis:
    """
    Main analysis function combining all vision detections.
    
    Args:
        frame: Current video frame
        head_pose: Head pose information from detector
        face_count: Number of faces detected
        phone_detected: Whether phone is detected
        session_id: Session identifier
    
    Returns:
        VisionAnalysis with complete detection results
    """
    
    state = get_session_state(session_id)
    now = time.time()
    state.frame_count += 1
    
    # Import screenshot function only when needed
    screenshot_path = None
    
    # ===== CRITICAL: Multiple Faces =====
    if face_count > 1:
        logger.warning(f"🚨 CRITICAL: {face_count} faces detected")
        state.multiple_faces_detected_time = now
        
        analysis = VisionAnalysis(
            timestamp=now,
            detection_type=DetectionType.MULTIPLE_FACES.value,
            alert_level=AlertLevel.CRITICAL.value,
            confidence=95.0,
            score=95,
            reason=f"Multiple faces detected ({face_count})",
            face_count=face_count,
            screenshot_taken=True,
        )
        
        # Take screenshot immediately
        screenshot_path = _take_screenshot(frame, session_id, "multiple_faces")
        if screenshot_path:
            analysis.screenshot_path = screenshot_path
        
        state.last_analysis = analysis
        return analysis
    
    # ===== CRITICAL: Phone Detected =====
    if phone_detected:
        logger.warning("🚨 CRITICAL: Mobile phone detected")
        
        # Cooldown check
        if (state.phone_detected_start is None or 
            (now - state.phone_detected_start) > SVEConfig.PHONE_ALERT_COOLDOWN):
            
            state.phone_detected_start = now
            
            analysis = VisionAnalysis(
                timestamp=now,
                detection_type=DetectionType.PHONE_DETECTED.value,
                alert_level=AlertLevel.CRITICAL.value,
                confidence=90.0,
                score=90,
                reason="Mobile phone detected in frame",
                phone_detected=True,
                screenshot_taken=True,
            )
            
            # Take screenshot
            screenshot_path = _take_screenshot(frame, session_id, "phone_detected")
            if screenshot_path:
                analysis.screenshot_path = screenshot_path
            
            state.last_analysis = analysis
            return analysis
    
    # ===== Check normal state first =====
    if head_pose:
        if head_pose.is_normal() and not phone_detected and face_count == 1:
            # Eyes on camera - NORMAL/LOW alert
            state.looking_away_start = None
            
            analysis = VisionAnalysis(
                timestamp=now,
                detection_type=DetectionType.EYES_ON_CAMERA.value,
                alert_level=AlertLevel.NONE.value,
                confidence=10.0,
                score=5,
                reason="Eyes on camera - Normal state",
                face_count=face_count,
            )
            
            state.last_analysis = analysis
            return analysis
    
    # ===== Check for Looking Away =====
    if head_pose and not head_pose.is_normal():
        # Start tracking looking away
        if state.looking_away_start is None:
            state.looking_away_start = now
            logger.info(f"⏱️ Looking away started at {now}")
        
        looking_away_duration = now - state.looking_away_start
        
        # MEDIUM: Looking away > 10 seconds
        if looking_away_duration >= SVEConfig.LOOKING_AWAY_LONG_THRESHOLD:
            logger.warning(f"⚠️ MEDIUM: Looking away for {looking_away_duration:.1f}s")
            
            # Check cooldown to avoid alert spam
            if (state.last_looking_away_alert is None or 
                (now - state.last_looking_away_alert) > SVEConfig.LOOKING_AWAY_ALERT_COOLDOWN):
                
                state.last_looking_away_alert = now
                
                analysis = VisionAnalysis(
                    timestamp=now,
                    detection_type=DetectionType.LOOKING_AWAY_LONG.value,
                    alert_level=AlertLevel.MEDIUM.value,
                    confidence=75.0,
                    score=70,
                    reason=f"Looking away for {looking_away_duration:.1f}s (> 10s threshold)",
                    looking_away_duration=looking_away_duration,
                    eyes_closed=head_pose.eyes_closed,
                    head_pose=asdict(head_pose),
                    screenshot_taken=True,
                )
                
                # Take screenshot
                screenshot_path = _take_screenshot(frame, session_id, "looking_away_long")
                if screenshot_path:
                    analysis.screenshot_path = screenshot_path
                
                state.last_analysis = analysis
                return analysis
        
        # MEDIUM: Looking away < 10 seconds
        elif looking_away_duration > 0:
            logger.debug(f"⏱️ MEDIUM: Looking away for {looking_away_duration:.1f}s (< 10s)")
            
            analysis = VisionAnalysis(
                timestamp=now,
                detection_type=DetectionType.LOOKING_AWAY_SHORT.value,
                alert_level=AlertLevel.MEDIUM.value,
                confidence=50.0,
                score=50,
                reason=f"Looking away for {looking_away_duration:.1f}s (< 10s threshold)",
                looking_away_duration=looking_away_duration,
                eyes_closed=head_pose.eyes_closed,
                head_pose=asdict(head_pose),
            )
            
            state.last_analysis = analysis
            return analysis
    
    # ===== Head Pose Change Detection =====
    if head_pose and state.last_head_pose:
        if _head_pose_changed(state.last_head_pose, head_pose):
            logger.info(
                f"🔄 HEAD POSE CHANGED: "
                f"{state.last_head_pose.direction} → {head_pose.direction}"
            )
            
            analysis = VisionAnalysis(
                timestamp=now,
                detection_type=DetectionType.HEAD_POSE_CHANGE.value,
                alert_level=AlertLevel.MEDIUM.value,
                confidence=60.0,
                score=60,
                reason=f"Head turned {head_pose.direction}",
                head_pose=asdict(head_pose),
                screenshot_taken=True,
            )
            
            # Take screenshot on significant head movement
            if head_pose.direction in ["left", "right", "up", "down"]:
                screenshot_path = _take_screenshot(
                    frame, session_id, f"head_pose_{head_pose.direction}"
                )
                if screenshot_path:
                    analysis.screenshot_path = screenshot_path
            
            state.last_head_pose = head_pose
            state.last_analysis = analysis
            return analysis
    
    # Update last head pose
    if head_pose:
        state.last_head_pose = head_pose
    
    # Reset looking away timer if back to normal
    if head_pose and head_pose.is_normal():
        state.looking_away_start = None
    
    # Default: All checks passed
    analysis = VisionAnalysis(
        timestamp=now,
        detection_type=DetectionType.NORMAL.value,
        alert_level=AlertLevel.NONE.value,
        confidence=5.0,
        score=10,
        reason="All checks normal",
        face_count=face_count,
    )
    
    state.last_analysis = analysis
    return analysis


def _head_pose_changed(pose1: HeadPose, pose2: HeadPose) -> bool:
    """Detect significant head pose change"""
    # Check if direction changed significantly
    direction_changed = pose1.direction != pose2.direction
    
    # Check if significant offset change
    h_offset_change = abs(pose2.horizontal_offset - pose1.horizontal_offset) > 0.1
    v_offset_change = abs(pose2.vertical_offset - pose1.vertical_offset) > 0.1
    
    return direction_changed or h_offset_change or v_offset_change


def _take_screenshot(frame: np.ndarray, session_id: str, event_name: str) -> Optional[str]:
    """
    Take and save a screenshot of the current frame.
    
    Args:
        frame: Current video frame
        session_id: Session identifier
        event_name: Name of the event (used in filename)
    
    Returns:
        Path to saved screenshot, or None if failed
    """
    try:
        # Create directory if needed
        screenshot_dir = SVEConfig.SCREENSHOT_DIR
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{session_id}_{event_name}_{timestamp}.jpg"
        filepath = os.path.join(screenshot_dir, filename)
        
        # Save screenshot
        if cv2.imwrite(filepath, frame):
            logger.info(f"📸 Screenshot saved: {filepath}")
            return filepath
        else:
            logger.error(f"❌ Failed to save screenshot: {filepath}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Screenshot error: {e}")
        return None


# ========== SCORE CALCULATION ==========

def calculate_suspicion_score(analysis: VisionAnalysis) -> float:
    """
    Calculate overall suspicion score (0-100).
    
    Higher score = More suspicious behavior
    """
    
    if analysis.alert_level == AlertLevel.CRITICAL.value:
        return 95.0
    
    if analysis.alert_level == AlertLevel.MEDIUM.value:
        if analysis.detection_type == DetectionType.LOOKING_AWAY_LONG.value:
            # Longer duration = higher score
            duration = analysis.looking_away_duration or 0
            score = min(80.0, 50.0 + (duration / 10.0) * 30.0)
            return score
        elif analysis.detection_type == DetectionType.HEAD_POSE_CHANGE.value:
            return 60.0
        else:
            return 50.0
    
    if analysis.alert_level == AlertLevel.NONE.value:
        return 5.0
    
    return 10.0


# ========== SESSION MANAGEMENT ==========

def reset_session(session_id: str):
    """Reset analysis state for a session"""
    if session_id in _session_states:
        _session_states[session_id] = SessionState(session_id=session_id)
        logger.info(f"✅ Session {session_id} state reset")


def get_session_summary(session_id: str) -> Dict:
    """Get summary of analysis for a session"""
    state = get_session_state(session_id)
    
    return {
        "session_id": session_id,
        "frame_count": state.frame_count,
        "last_analysis": asdict(state.last_analysis) if state.last_analysis else None,
        "looking_away_active": state.looking_away_start is not None,
        "looking_away_start": state.looking_away_start,
    }


# ========== INTEGRATION HELPERS ==========

def create_analysis_from_detectors(
    frame: np.ndarray,
    gaze_result: Optional[Dict],
    pose_result: Optional[Dict],
    session_id: str = "default"
) -> VisionAnalysis:
    """
    Create comprehensive analysis from detector outputs.
    
    Args:
        frame: Current video frame
        gaze_result: Output from eye_gaze_tracking.analyze_gaze()
        pose_result: Output from head_pose_estimation.estimate_head_pose()
        session_id: Session identifier
    
    Returns:
        VisionAnalysis result
    """
    
    # Extract data from detectors
    face_count = 1
    phone_detected = False
    head_pose = None
    
    # From gaze result
    if gaze_result:
        face_count = gaze_result.get("face_count", 1)
    
    # From pose result
    if pose_result:
        phone_detected = pose_result.get("phone_detected", False)
        face_count = max(face_count, pose_result.get("person_count", 1))
        
        # Build HeadPose object
        if pose_result.get("status") == "normal":
            head_pose = HeadPose(
                direction=pose_result.get("direction", "center"),
                horizontal_offset=pose_result.get("offset_horizontal", 0),
                vertical_offset=pose_result.get("offset_vertical", 0),
                eyes_closed=pose_result.get("eyes_closed", False),
            )
    
    # Run analysis
    return analyze_frame(
        frame=frame,
        head_pose=head_pose,
        face_count=face_count,
        phone_detected=phone_detected,
        session_id=session_id
    )
