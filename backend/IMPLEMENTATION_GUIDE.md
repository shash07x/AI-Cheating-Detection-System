# AI Cheating Detection System - Analysis Engines Implementation Guide

## Overview
Two comprehensive analysis engines have been developed:
1. **Stable Vision Engine (SVE)** - Face and visual analysis
2. **Enhanced Audio Engine (EAAE)** - Audio authenticity detection

---

## 1. STABLE VISION ENGINE (SVE)

### Location
`backend/app/services/stable_vision_engine.py`

### Features

#### 1.1 Eye Movement Detection (LOW Alert)
- **Detection**: Eyes looking at camera
- **Alert Level**: LOW (confidence: 10%)
- **Score**: 5-10
- **Action**: No screenshot needed
- **Reason**: Natural behavior, minimal concern

#### 1.2 Looking Away < 10 seconds (MEDIUM Alert)
- **Duration**: Less than 10 seconds
- **Alert Level**: MEDIUM (confidence: 50%)
- **Score**: 50
- **Action**: No screenshot
- **Reasoning**: Brief gaze aversion is natural; monitor pattern

#### 1.3 Looking Away > 10 seconds (MEDIUM Alert)
- **Duration**: Greater than 10 seconds
- **Alert Level**: MEDIUM (confidence: 75%)
- **Score**: 70
- **Action**: **TAKE SCREENSHOT**
- **Reasoning**: Prolonged gaze aversion indicates suspicious behavior
- **Cooldown**: 5 seconds (prevents alert spam)

#### 1.4 Head Pose Changes (MEDIUM Alert)
- **Detection**: Head turning (up, down, left, right)
- **Directions Detected**:
  - Left/Right: Horizontal deviation > 0.15
  - Up/Down: Vertical deviation > 0.20
- **Alert Level**: MEDIUM (confidence: 60%)
- **Score**: 60
- **Action**: **TAKE SCREENSHOT** for significant movements
- **Example**: Student turns to look at neighbor

#### 1.5 Multiple Faces (CRITICAL Alert)
- **Detection**: Face count > 1
- **Alert Level**: CRITICAL (confidence: 95%)
- **Score**: 95
- **Action**: **IMMEDIATE SCREENSHOT**
- **Reasoning**: Indicates proxy test-taking or cheating with accomplice

#### 1.6 Mobile Phone Detection (CRITICAL Alert)
- **Detection**: Phone/device in frame
- **Alert Level**: CRITICAL (confidence: 90%)
- **Score**: 90
- **Action**: **IMMEDIATE SCREENSHOT**
- **Cooldown**: 30 seconds (prevents multiple rapid alerts)
- **Reasoning**: Phone indicates external resources/communication

---

## 2. ENHANCED AUDIO ENGINE (EAAE)

### Location
`backend/app/services/enhanced_audio_engine.py`

### Features

#### 2.1 AI Voice Detection (CRITICAL Alert)
- **Method**: MFCC + Spectral Analysis
- **Detection**: Synthetic/AI-generated voice
- **Indicators**:
  - Low pitch variation (< 0.15) - unnatural consistency
  - Consistent energy (std < 0.01) - robotic stability
  - Perfect speech rate (140-160 WPM) - too regular
  - Insufficient pauses (pause ratio < 0.05)
  - Uniform MFCC patterns (std < 5.0)
- **Alert Level**: CRITICAL (confidence > 70%)
- **Score**: 90
- **Action**: Immediate flagging
- **Reasoning**: AI voice = someone else answering questions

#### 2.2 Prolonged Silence (MEDIUM Alert)
- **Threshold**: > 5 seconds of silence
- **Alert Level**: MEDIUM (confidence: 75%)
- **Score**: 60
- **Reasoning**: Student may be consulting resources, not thinking

#### 2.3 Excessive Background Noise (MEDIUM Alert)
- **Threshold**: Energy > 0.3 RMS
- **Alert Level**: MEDIUM (confidence: 70%)
- **Score**: 65
- **Reasoning**: May indicate shared test location or video call

#### 2.4 Monotone Speech (MEDIUM Alert)
- **Detection**: Pitch variation < 0.3
- **Alert Level**: MEDIUM (confidence: 60%)
- **Score**: 55
- **Reasoning**: Reading from notes/script rather than thinking

#### 2.5 Unusual Speech Rate (MEDIUM Alert)
- **Normal Range**: 150±35% WPM (i.e., 98-203 WPM)
- **Alert Level**: MEDIUM (confidence: 55%)
- **Score**: 50
- **Reasoning**: Too slow = reading; too fast = rushed/nervous

---

## 3. INTEGRATION GUIDE

### 3.1 Using Stable Vision Engine

```python
from app.services.stable_vision_engine import (
    analyze_frame,
    HeadPose,
    VisionAnalysis,
    reset_session,
    get_session_summary
)

# Create head pose from detector output
head_pose = HeadPose(
    direction="left",
    horizontal_offset=-0.25,
    vertical_offset=0.05,
    eyes_closed=False
)

# Analyze frame
analysis: VisionAnalysis = analyze_frame(
    frame=video_frame,
    head_pose=head_pose,
    face_count=1,
    phone_detected=False,
    session_id="session_123"
)

# Get results
print(f"Alert Level: {analysis.alert_level}")
print(f"Score: {analysis.score}")
print(f"Screenshot: {analysis.screenshot_path}")

if analysis.screenshot_taken:
    # Save screenshot path to database
    pass
```

### 3.2 Using Enhanced Audio Engine

```python
from app.services.enhanced_audio_engine import (
    analyze_audio_chunk,
    AudioAnalysis,
    get_audio_session_summary
)

# Analyze audio chunk
analysis: AudioAnalysis = analyze_audio_chunk(
    audio_bytes=audio_data,
    session_id="session_123",
    sr=16000
)

# Get results
print(f"Alert Level: {analysis.alert_level}")
print(f"Score: {analysis.score}")
print(f"AI Voice Detected: {analysis.is_ai_voice}")

if analysis.is_ai_voice:
    # Critical: Prevent submission
    pass
```

### 3.3 Combined Analysis

```python
# Create helper function
def perform_complete_analysis(
    frame,
    audio_bytes,
    head_pose_data,
    session_id
):
    # Vision analysis
    vision_analysis = analyze_frame(
        frame=frame,
        head_pose=head_pose_data,
        session_id=session_id
    )
    
    # Audio analysis
    audio_analysis = analyze_audio_chunk(
        audio_bytes=audio_bytes,
        session_id=session_id
    )
    
    # Combine results
    combined_score = (vision_analysis.score + audio_analysis.score) / 2
    
    # Determine overall alert
    if vision_analysis.alert_level == "critical" or audio_analysis.alert_level == "critical":
        overall_alert = "critical"
    else:
        overall_alert = max(
            [vision_analysis.alert_level, audio_analysis.alert_level],
            key=lambda x: alert_level_to_int(x)
        )
    
    return {
        "overall_alert": overall_alert,
        "combined_score": combined_score,
        "vision": vision_analysis.to_dict(),
        "audio": audio_analysis.to_dict(),
    }
```

---

## 4. ALERT THRESHOLDS SUMMARY

### Vision Engine Alerts
| Detection | Alert Level | Confidence | Score | Screenshot |
|-----------|------------|-----------|-------|-----------|
| Eyes on camera | NONE | 10% | 5 | No |
| Looking away < 10s | MEDIUM | 50% | 50 | No |
| Looking away > 10s | MEDIUM | 75% | 70 | Yes |
| Head turned | MEDIUM | 60% | 60 | Yes |
| Multiple faces | CRITICAL | 95% | 95 | Yes |
| Phone detected | CRITICAL | 90% | 90 | Yes |

### Audio Engine Alerts
| Detection | Alert Level | Confidence | Score | Reason |
|-----------|------------|-----------|-------|--------|
| Normal speech | NONE | 5% | 10 | - |
| AI voice | CRITICAL | 70%+ | 90 | Synthetic/deepfake |
| Prolonged silence | MEDIUM | 75% | 60 | Consulting resources |
| Excessive noise | MEDIUM | 70% | 65 | Shared location |
| Monotone | MEDIUM | 60% | 55 | Reading script |
| Unusual speech rate | MEDIUM | 55% | 50 | Unnatural pace |

---

## 5. SCORE CALCULATION

### Vision Score Factors
```
Critical Events (Priority):
- Multiple faces: 95 points
- Phone detected: 90 points

Pattern-based Events:
- Looking away > 10s: 50-80 points (based on duration)
- Head movement: 60 points
- Looking away < 10s: 50 points

Normal State:
- Eyes on camera: 5-10 points
```

### Audio Score Factors
```
Critical: AI voice detection
- Confidence 70-85%: 80 points
- Confidence 85%+: 90 points

Medium Events:
- Prolonged silence: 60 points
- Background noise: 65 points
- Monotone speech: 55 points
- Unusual speech rate: 50 points
- Normal speaking: 10 points
```

---

## 6. CONFIGURATION PARAMETERS

### Stable Vision Engine Config (SVEConfig)
```python
LOOKING_AWAY_SHORT_THRESHOLD = 10.0  # seconds
LOOKING_AWAY_LONG_THRESHOLD = 10.0   # seconds
HEAD_POSE_H_THRESHOLD = 0.15         # horizontal
HEAD_POSE_V_THRESHOLD = 0.20         # vertical
EYES_CLOSED_THRESHOLD = 5.0          # pixels
LOOKING_AWAY_ALERT_COOLDOWN = 5.0    # seconds
PHONE_ALERT_COOLDOWN = 30.0          # seconds
SCREENSHOT_DIR = "backend/evidence"
```

### Enhanced Audio Engine Config (EAAEConfig)
```python
SILENCE_THRESHOLD = 0.01             # RMS
NOISE_THRESHOLD = 0.3                # RMS
NORMAL_SPEECH_MIN = 0.05             # RMS
NORMAL_SPEECH_MAX = 0.2              # RMS
NORMAL_SPEECH_RATE = 150             # WPM
SPEECH_RATE_TOLERANCE = 0.35         # 35%
NORMAL_PITCH_VARIATION_MIN = 0.3     # threshold
AI_VOICE_CONFIDENCE_THRESHOLD = 0.70
SILENCE_ALERT_THRESHOLD = 5.0        # seconds
```

---

## 7. FILE LOCATIONS

### Vision Analysis
- Engine: `backend/app/services/stable_vision_engine.py`
- Integrations:
  - Eye gaze: `backend/app/services/eye_gaze_tracking.py`
  - Head pose: `backend/app/services/head_pose_estimation.py`
  - Face detection: `backend/app/services/face_detection.py`

### Audio Analysis
- Engine: `backend/app/services/enhanced_audio_engine.py`
- Supporting modules:
  - Audio AI: `backend/app/services/audio_ai.py`
  - Features: `backend/app/services/audio_features_extractor.py`
  - Preprocessing: `backend/app/services/audio_preprocess.py`

### Evidence/Screenshots
- Directory: `backend/evidence/`
- Naming: `{session_id}_{event_name}_{timestamp}.jpg`

---

## 8. NEXT STEPS

1. **Integration**: Connect engines to route handlers
2. **Testing**: Validate with test videos/audio
3. **Tuning**: Adjust thresholds based on real data
4. **Database**: Store analysis results and screenshots
5. **UI**: Display alerts and scores in dashboard

---

## 9. TROUBLESHOOTING

### Vision Engine Issues
- **No face detected**: Check YOLO model loading (`eye_gaze_tracking.py`)
- **Multiple false positives**: Increase `LOOKING_AWAY_ALERT_COOLDOWN`
- **Screenshot not saving**: Check `backend/evidence/` directory permissions

### Audio Engine Issues
- **No audio features**: Install librosa (`pip install librosa`)
- **AI detection too sensitive**: Lower `AI_VOICE_CONFIDENCE_THRESHOLD`
- **Speech rate errors**: Verify audio sample rate (should be 16kHz)

---

Generated: March 12, 2026
Status: ✅ Complete
Version: 1.0
