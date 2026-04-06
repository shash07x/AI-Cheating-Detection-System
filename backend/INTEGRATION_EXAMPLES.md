"""
Quick Reference: Using SVE and EAAE in Your Routes

This file shows practical examples of integrating the analysis engines.
"""

# ============================================================================
# EXAMPLE 1: Vision Analysis in Video Route
# ============================================================================

from flask import Blueprint
from app.services.stable_vision_engine import (
    analyze_frame,
    HeadPose,
    reset_session,
)
from app.services.head_pose_estimation import estimate_head_pose
import cv2

def handle_video_frame(frame_bytes, session_id):
    """
    Process incoming video frame through vision engine.
    Called per video frame during interview.
    """
    
    # Decode frame
    frame = cv2.imdecode(frame_bytes, cv2.IMREAD_COLOR)
    
    # Run head pose detection
    pose_result = estimate_head_pose(frame)
    
    # Convert to HeadPose object
    if pose_result.get('status') == 'normal':
        head_pose = HeadPose(
            direction=pose_result.get('direction', 'center'),
            horizontal_offset=pose_result.get('offset_horizontal', 0),
            vertical_offset=pose_result.get('offset_vertical', 0),
            eyes_closed=pose_result.get('eyes_closed', False),
        )
    else:
        head_pose = None
    
    # Detect phone and multiple faces
    phone_detected = pose_result.get('phone_detected', False)
    person_count = pose_result.get('person_count', 1)
    
    # Run analysis
    analysis = analyze_frame(
        frame=frame,
        head_pose=head_pose,
        face_count=person_count,
        phone_detected=phone_detected,
        session_id=session_id
    )
    
    # Store results
    result = analysis.to_dict()
    
    # If screenshot taken, store path
    if analysis.screenshot_taken and analysis.screenshot_path:
        # Save to database
        save_evidence(
            session_id=session_id,
            evidence_type=analysis.detection_type,
            screenshot_path=analysis.screenshot_path,
            alert_level=analysis.alert_level,
            score=analysis.score
        )
    
    # Check for critical alerts
    if analysis.alert_level == 'critical':
        flag_session_for_review(session_id, analysis)
    
    return result


# ============================================================================
# EXAMPLE 2: Audio Analysis in Audio Route
# ============================================================================

from app.services.enhanced_audio_engine import (
    analyze_audio_chunk,
    get_audio_session_summary,
)

def handle_audio_chunk(audio_bytes, session_id):
    """
    Process incoming audio chunk through audio engine.
    Called for each audio segment during interview.
    """
    
    # Analyze audio
    analysis = analyze_audio_chunk(
        audio_bytes=audio_bytes,
        session_id=session_id,
        sr=16000  # 16kHz sample rate
    )
    
    result = analysis.to_dict()
    
    # Check for AI voice detection
    if analysis.is_ai_voice:
        logger.critical(f"🚨 AI VOICE DETECTED in {session_id}")
        flag_session_critical(
            session_id=session_id,
            reason="AI-generated voice detected",
            confidence=analysis.confidence
        )
    
    # Store alert  
    if analysis.alert_level != 'none':
        store_audio_alert(
            session_id=session_id,
            alert_level=analysis.alert_level,
            score=analysis.score,
            reason=analysis.reason,
            timestamp=analysis.timestamp
        )
    
    return result


# ============================================================================
# EXAMPLE 3: Complete Session Analysis Pipeline
# ============================================================================

def analyze_complete_session(session_id):
    """
    Perform comprehensive analysis at end of session.
    """
    from app.services.stable_vision_engine import get_session_summary as get_vision_summary
    from app.services.enhanced_audio_engine import get_audio_session_summary
    
    # Get summaries
    vision_summary = get_vision_summary(session_id)
    audio_summary = get_audio_session_summary(session_id)
    
    # Calculate composite score
    vision_score = vision_summary.get('last_analysis', {}).get('score', 0)
    audio_score = audio_summary.get('last_analysis', {}).get('score', 0)
    
    composite_score = (vision_score + audio_score) / 2
    
    # Determine overall assessment
    assessment = {
        'session_id': session_id,
        'composite_score': composite_score,
        'vision_analysis': vision_summary,
        'audio_analysis': audio_summary,
        'recommendation': determine_recommendation(composite_score, vision_summary, audio_summary),
        'flagged_for_review': composite_score > 70 or audio_summary.get('ai_detections', 0) > 0,
    }
    
    return assessment


def determine_recommendation(score, vision_summary, audio_summary):
    """
    Recommend action based on analysis.
    """
    if audio_summary.get('ai_detections', 0) > 0:
        return "REJECT - AI voice detected"
    
    if score > 85:
        return "MANUAL REVIEW - Multiple red flags"
    
    if score > 70:
        return "LIKELY FRAUDULENT - Significant concerns"
    
    if score > 50:
        return "REVIEW - Some suspicious behavior"
    
    if score > 30:
        return "ACCEPTABLE - Minor concerns only"
    
    return "CLEAR - No fraud indicators"


# ============================================================================
# EXAMPLE 4: Real-time Dashboard Update
# ============================================================================

from app.extensions import socketio

@socketio.on('request_analysis_update')
def send_analysis_update(data):
    """
    Send real-time analysis updates to dashboard.
    Called continuously during interview.
    """
    session_id = data.get('session_id')
    
    # Get latest analyses
    vision_summary = get_session_summary(session_id)
    audio_summary = get_audio_session_summary(session_id)
    
    # Last analyses
    last_vision = vision_summary.get('last_analysis')
    last_audio = audio_summary.get('last_analysis')
    
    # Current scores
    current_score = max(
        last_vision.get('score', 0) if last_vision else 0,
        last_audio.get('score', 0) if last_audio else 0
    )
    
    # Send to dashboard
    socketio.emit('analysis_update', {
        'session_id': session_id,
        'current_score': current_score,
        'vision_alert': last_vision.get('alert_level') if last_vision else 'none',
        'audio_alert': last_audio.get('alert_level') if last_audio else 'none',
        'vision_reason': last_vision.get('reason') if last_vision else '',
        'audio_reason': last_audio.get('reason') if last_audio else '',
        'timestamp': time.time(),
    })


# ============================================================================
# EXAMPLE 5: Alert Handling with Cooldowns
# ============================================================================

class AlertManager:
    """Manage alerts with cooldowns to prevent spam."""
    
    def __init__(self):
        self.last_alert_time = {}
        self.alert_cooldowns = {
            'looking_away_long': 5.0,
            'phone_detected': 30.0,
            'ai_voice': 10.0,
            'excessive_noise': 15.0,
        }
    
    def should_alert(self, alert_type: str) -> bool:
        """Check if alert should be sent (respecting cooldowns)."""
        now = time.time()
        last_time = self.last_alert_time.get(alert_type, 0)
        cooldown = self.alert_cooldowns.get(alert_type, 0)
        
        if now - last_time >= cooldown:
            self.last_alert_time[alert_type] = now
            return True
        return False
    
    def process_analysis(self, analysis):
        """Process analysis and send alert if appropriate."""
        if analysis.alert_level == 'critical':
            if self.should_alert(analysis.detection_type):
                send_alert_notification(analysis)
                return True
        
        elif analysis.alert_level == 'medium':
            if self.should_alert(analysis.detection_type):
                log_alert(analysis)
                return True
        
        return False


# ============================================================================
# EXAMPLE 6: Batch Analysis of Recorded Interview
# ============================================================================

def analyze_recorded_interview(video_path, audio_path, session_id):
    """
    Analyze complete recorded interview (post-interview analysis).
    More thorough than real-time.
    """
    import cv2
    import librosa
    
    # Reset session state
    reset_session(session_id)
    
    # Process video
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    critical_frames = []
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Run analysis every 30 frames (~1 second at 30fps)
        if frame_count % 30 == 0:
            analysis = handle_video_frame(cv2.imencode('.jpg', frame)[1].tobytes(), session_id)
            
            if analysis.get('alert_level') == 'critical':
                critical_frames.append({
                    'frame': frame_count,
                    'alert': analysis['detection_type'],
                })
    
    cap.release()
    
    # Process audio
    y, sr = librosa.load(audio_path, sr=16000)
    
    # Split into chunks (e.g., 2 seconds each)
    chunk_size = sr * 2
    for i in range(0, len(y), chunk_size):
        chunk = y[i:i+chunk_size]
        audio_bytes = (chunk * 32767).astype(np.int16).tobytes()
        
        analysis = handle_audio_chunk(audio_bytes, session_id)
        
        if analysis.get('is_ai_voice'):
            logger.warning(f"AI voice detected at {i/sr:.1f}s")
    
    # Generate final report
    return generate_interview_report(session_id, critical_frames)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def save_evidence(session_id, evidence_type, screenshot_path, alert_level, score):
    """Save evidence to database."""
    # TODO: Implement database storage
    pass


def flag_session_for_review(session_id, analysis):
    """Flag session for manual review."""
    logger.warning(f"🚩 Session {session_id} flagged for review: {analysis.reason}")
    # TODO: Update database
    pass


def flag_session_critical(session_id, reason, confidence):
    """Flag session as critical issue."""
    logger.critical(f"🚨 CRITICAL {session_id}: {reason} (confidence: {confidence:.1%})")
    # TODO: Notify administrators
    pass


def store_audio_alert(session_id, alert_level, score, reason, timestamp):
    """Store audio alert."""
    # TODO: Save to database
    pass


def send_alert_notification(analysis):
    """Send notification about alert."""
    # TODO: Send email/SMS/push notification
    pass


def log_alert(analysis):
    """Log alert for records."""
    logger.warning(f"Alert: {analysis.alert_level} - {analysis.reason}")


def generate_interview_report(session_id, critical_frames):
    """Generate comprehensive report."""
    # TODO: Create detailed report
    pass


# ============================================================================
# USAGE SUMMARY
# ============================================================================

"""
Integration Checklist:

Vision Engine (SVE):
□ Import analyze_frame and HeadPose
□ Get head pose from detector
□ Call analyze_frame with frame + pose + counts
□ Check alert_level for critical events
□ Save screenshots if screenshot_taken == True
□ Use cooldowns to prevent alert spam

Audio Engine (EAAE):
□ Import analyze_audio_chunk
□ Pass audio bytes and session_id
□ Check for is_ai_voice flag (CRITICAL)
□ Store all medium+ alerts
□ Use get_audio_session_summary for reports

Recommended Alert Actions:
- CRITICAL → Immediately stop interview, flag for review
- MEDIUM → Log alert, update dashboard, may require approval
- LOW/NONE → Continue normal processing

For best results:
1. Tune thresholds based on actual user behavior
2. Collect baseline metrics from legitimate users
3. Implement machine learning calibration over time
4. Manual review all critical flags before taking action
"""
