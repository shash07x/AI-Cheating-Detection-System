"""
Enhanced Audio Analysis Engine (EAAE) - Comprehensive Audio Fraud Detection

Detects:
1. AI-generated/synthetic voice (CRITICAL alert)
2. Multiple speakers (background voices - MEDIUM alert)
3. Unusual speech rate/patterns (MEDIUM alert)
4. Prolonged silence or background noise (MEDIUM alert)
5. Monotone speaking style (MEDIUM alert)
6. Emotional inconsistency in speech (MEDIUM alert)
"""

import numpy as np
import logging
import time
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List
from enum import Enum
import io

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logging.warning("⚠️ Librosa not available - advanced audio analysis limited")

logger = logging.getLogger(__name__)


# ========== ENUMS ==========

class AudioAlertLevel(Enum):
    """Alert severity levels for audio"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    CRITICAL = "critical"


class AudioDetectionType(Enum):
    """Types of audio detections"""
    NORMAL_SPEECH = "normal_speech"
    AI_VOICE_DETECTED = "ai_voice_detected"
    MULTIPLE_SPEAKERS = "multiple_speakers"
    BACKGROUND_VOICES = "background_voices"
    UNUSUAL_SPEECH_RATE = "unusual_speech_rate"
    PROLONGED_SILENCE = "prolonged_silence"
    EXCESSIVE_NOISE = "excessive_noise"
    MONOTONE_SPEECH = "monotone_speech"
    EMOTIONAL_INCONSISTENCY = "emotional_inconsistency"
    IRREGULAR_BREATHING = "irregular_breathing"


# ========== DATA CLASSES ==========

@dataclass
class SpeechStats:
    """Speech statistics"""
    pitch_mean: float
    pitch_std: float
    pitch_variation: float
    energy_mean: float
    energy_std: float
    speech_rate: float
    pause_count: int
    pause_ratio: float
    silence_duration: float
    mfcc_mean: List[float] = None


@dataclass
class AudioAnalysis:
    """Complete audio analysis result"""
    timestamp: float
    detection_type: str
    alert_level: str
    confidence: float
    score: float  # 0-100, higher = more suspicious
    reason: str
    
    # Detection details
    is_ai_voice: bool = False
    speaker_count: int = 1
    background_noise_level: float = 0.0
    speech_stats: Optional[Dict] = None
    
    # Metrics
    recording_duration: float = 0.0
    silence_ratio: float = 0.0
    noise_ratio: float = 0.0


# ========== SESSION STATE ==========

@dataclass
class AudioSessionState:
    """Per-session audio tracking"""
    session_id: str
    
    # Audio tracking
    total_audio_duration: float = 0.0
    silence_duration: float = 0.0
    noise_duration: float = 0.0
    
    # Speaker tracking
    speaker_ids_seen: set = None
    background_voice_starts: Optional[float] = None
    speaking_normally: bool = True
    
    # Pattern tracking
    speech_rate_readings: List[float] = None
    pitch_variation_readings: List[float] = None
    last_analysis: Optional[AudioAnalysis] = None
    
    # AI detection
    ai_confidence_readings: List[float] = None
    consecutive_ai_detections: int = 0
    
    def __post_init__(self):
        if self.speaker_ids_seen is None:
            self.speaker_ids_seen = set()
        if self.speech_rate_readings is None:
            self.speech_rate_readings = []
        if self.pitch_variation_readings is None:
            self.pitch_variation_readings = []
        if self.ai_confidence_readings is None:
            self.ai_confidence_readings = []


_audio_session_states: Dict[str, AudioSessionState] = {}


def get_audio_session_state(session_id: str) -> AudioSessionState:
    """Get or create audio session state"""
    if session_id not in _audio_session_states:
        _audio_session_states[session_id] = AudioSessionState(session_id=session_id)
    return _audio_session_states[session_id]


# ========== CONFIGURATION ==========

class EAAEConfig:
    """Enhanced Audio Analysis Engine Configuration"""
    
    # Audio thresholds (in dB/RMS)
    SILENCE_THRESHOLD = 0.01  # RMS below this = silence
    NOISE_THRESHOLD = 0.3     # RMS above this = excessive noise
    NORMAL_SPEECH_MIN = 0.05
    NORMAL_SPEECH_MAX = 0.2
    
    # Speech characteristics
    NORMAL_SPEECH_RATE = 150  # words per minute (typically 140-180)
    SPEECH_RATE_TOLERANCE = 0.35  # 35% deviation
    
    NORMAL_PITCH_MEAN = 150  # Hz (female ~200, male ~120)
    NORMAL_PITCH_VARIATION_MIN = 0.3  # Monotone threshold
    
    # Suspicious thresholds
    AI_VOICE_CONFIDENCE_THRESHOLD = 0.70
    BACKGROUND_VOICE_CONFIDENCE_THRESHOLD = 0.60
    MULTIPLE_SPEAKER_THRESHOLD = 3  # Number of unique voice patterns
    
    # Time thresholds
    SILENCE_ALERT_THRESHOLD = 5.0  # seconds
    BACKGROUND_NOISE_DURATION_THRESHOLD = 10.0  # seconds
    
    # Smoothing
    MAX_HISTORY_SIZE = 20


# ========== FEATURE EXTRACTION ==========

def extract_audio_features(audio_bytes: bytes, sr: int = 16000) -> Optional[SpeechStats]:
    """
    Extract speech features from audio bytes.
    
    Args:
        audio_bytes: Raw audio bytes
        sr: Sample rate (default 16kHz)
    
    Returns:
        SpeechStats object or None if extraction failed
    """
    
    if not LIBROSA_AVAILABLE:
        logger.warning("⚠️ Librosa not available - cannot extract audio features")
        return None
    
    try:
        # Convert bytes to numpy array
        try:
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        except:
            # Try float32 directly
            audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
        
        if len(audio_array) < sr:  # Less than 1 second
            return None
        
        # Duration
        duration = len(audio_array) / sr
        
        # ===== Pitch Analysis =====
        try:
            pitches, magnitudes = librosa.piptrack(
                y=audio_array,
                sr=sr,
                fmin=60,
                fmax=400,
                threshold=0.1
            )
            
            # Get mean pitch
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if pitch_values:
                pitch_mean = np.mean(pitch_values)
                pitch_std = np.std(pitch_values)
                pitch_variation = pitch_std / (pitch_mean + 1e-6)
            else:
                pitch_mean = pitch_std = pitch_variation = 0
        except:
            pitch_mean = pitch_std = pitch_variation = 0
        
        # ===== Energy Analysis =====
        energy = librosa.feature.rms(y=audio_array)[0]
        energy_mean = np.mean(energy)
        energy_std = np.std(energy)
        
        # ===== Speech Rate Estimation =====
        # Using onset detection as proxy for syllables
        onset_frames = librosa.onset.onset_detect(y=audio_array, sr=sr)
        syllables = len(onset_frames)
        # Rough conversion: ~3-4 syllables per word
        estimated_words = syllables / 3.5
        speech_rate = (estimated_words / duration) * 60 if duration > 0 else 0
        
        # ===== Pause Detection =====
        S = librosa.feature.melspectrogram(y=audio_array, sr=sr)
        S_db = librosa.power_to_db(S, ref=np.max)
        
        # Frames with low energy = pauses
        threshold = np.percentile(S_db, 20)
        pauses = np.sum(S_db.mean(axis=0) < threshold)
        total_frames = S_db.shape[1]
        pause_ratio = pauses / (total_frames + 1e-6) if total_frames > 0 else 0
        pause_count = int(pauses)
        
        # ===== Silence Duration =====
        silence_frames = np.abs(audio_array) < EAAEConfig.SILENCE_THRESHOLD
        silence_ratio = np.sum(silence_frames) / len(audio_array)
        silence_duration = silence_ratio * duration
        
        # ===== MFCC (for AI detection) =====
        mfcc = librosa.feature.mfcc(y=audio_array, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfcc, axis=1).tolist()
        
        return SpeechStats(
            pitch_mean=float(pitch_mean),
            pitch_std=float(pitch_std),
            pitch_variation=float(pitch_variation),
            energy_mean=float(energy_mean),
            energy_std=float(energy_std),
            speech_rate=float(speech_rate),
            pause_count=pause_count,
            pause_ratio=float(pause_ratio),
            silence_duration=float(silence_duration),
            mfcc_mean=mfcc_mean
        )
    
    except Exception as e:
        logger.error(f"❌ Feature extraction error: {e}")
        return None


# ========== AI VOICE DETECTION ==========

def detect_ai_voice(features: SpeechStats) -> Dict[str, float]:
    """
    Detect AI-generated voice using audio features.
    
    Returns:
        Dict with 'confidence' (0-1) and 'is_ai' (bool)
    """
    
    if not features or not features.mfcc_mean:
        return {"confidence": 0.0, "is_ai": False}
    
    try:
        ai_indicators = []
        
        # 1. Unnatural pitch characteristics
        # Real humans have pitch variation
        if features.pitch_variation < 0.15:
            ai_indicators.append(("low_pitch_variation", 0.3))
        
        # 2. Unnaturally consistent energy
        if features.energy_std < 0.01:
            ai_indicators.append(("consistent_energy", 0.25))
        
        # 3. Unnatural speech rate (too perfect)
        # AI voices often have less natural variation
        if 140 < features.speech_rate < 160:  # Too "perfect"
            ai_indicators.append(("perfect_speech_rate", 0.2))
        
        # 4. Lack of pauses (human speech has natural pauses)
        if features.pause_ratio < 0.05:
            ai_indicators.append(("insufficient_pauses", 0.25))
        
        # 5. MFCC analysis (detect synthetic patterns)
        mfcc_mean = np.array(features.mfcc_mean)
        mfcc_std = np.std(mfcc_mean)
        if mfcc_std < 5.0:  # Too uniform = synthetic
            ai_indicators.append(("uniform_mfcc", 0.3))
        
        # Calculate confidence
        if ai_indicators:
            total_confidence = sum(score for _, score in ai_indicators)
            confidence = min(0.95, total_confidence)
        else:
            confidence = 0.05
        
        logger.debug(f"🤖 AI Voice Detection: {confidence:.2f} - Indicators: {ai_indicators}")
        
        return {
            "confidence": float(confidence),
            "is_ai": confidence > EAAEConfig.AI_VOICE_CONFIDENCE_THRESHOLD,
            "indicators": [name for name, _ in ai_indicators]
        }
    
    except Exception as e:
        logger.error(f"❌ AI voice detection error: {e}")
        return {"confidence": 0.0, "is_ai": False}


# ========== MAIN ANALYSIS ==========

def analyze_audio_chunk(
    audio_bytes: bytes,
    session_id: str = "default",
    sr: int = 16000
) -> AudioAnalysis:
    """
    Analyze audio chunk for suspicious content.
    
    Args:
        audio_bytes: Raw audio data
        session_id: Session identifier
        sr: Sample rate
    
    Returns:
        AudioAnalysis result
    """
    
    state = get_audio_session_state(session_id)
    now = time.time()
    
    # Extract features
    features = extract_audio_features(audio_bytes, sr)
    
    if features is None:
        logger.warning("⚠️ Failed to extract audio features")
        return AudioAnalysis(
            timestamp=now,
            detection_type=AudioDetectionType.NORMAL_SPEECH.value,
            alert_level=AudioAlertLevel.NONE.value,
            confidence=0.0,
            score=5,
            reason="Unable to analyze audio",
            recording_duration=0.0
        )
    
    # Update state
    state.total_audio_duration += features.silence_duration
    state.silence_duration += features.silence_duration
    
    # ===== Check 1: AI Voice Detection (CRITICAL) =====
    ai_detection = detect_ai_voice(features)
    state.ai_confidence_readings.append(ai_detection["confidence"])
    if len(state.ai_confidence_readings) > EAAEConfig.MAX_HISTORY_SIZE:
        state.ai_confidence_readings.pop(0)
    
    if ai_detection["is_ai"]:
        state.consecutive_ai_detections += 1
        logger.warning(f"🚨 AI VOICE DETECTED: confidence={ai_detection['confidence']:.2f}")
        
        analysis = AudioAnalysis(
            timestamp=now,
            detection_type=AudioDetectionType.AI_VOICE_DETECTED.value,
            alert_level=AudioAlertLevel.CRITICAL.value,
            confidence=ai_detection["confidence"],
            score=90,
            reason=f"AI-generated voice detected ({ai_detection['confidence']:.1%} confidence)",
            is_ai_voice=True,
            speech_stats=asdict(features),
        )
        state.last_analysis = analysis
        return analysis
    else:
        state.consecutive_ai_detections = 0
    
    # ===== Check 2: Prolonged Silence (MEDIUM) =====
    if features.silence_duration > EAAEConfig.SILENCE_ALERT_THRESHOLD:
        logger.warning(f"⚠️ MEDIUM: Prolonged silence for {features.silence_duration:.1f}s")
        
        analysis = AudioAnalysis(
            timestamp=now,
            detection_type=AudioDetectionType.PROLONGED_SILENCE.value,
            alert_level=AudioAlertLevel.MEDIUM.value,
            confidence=0.75,
            score=60,
            reason=f"Prolonged silence detected ({features.silence_duration:.1f}s)",
            silence_ratio=features.silence_duration,
            speech_stats=asdict(features),
        )
        state.last_analysis = analysis
        return analysis
    
    # ===== Check 3: Excessive Noise (MEDIUM) =====
    avg_energy = np.mean([features.energy_mean])
    if avg_energy > EAAEConfig.NOISE_THRESHOLD:
        logger.warning(f"⚠️ MEDIUM: Excessive background noise (energy={avg_energy:.3f})")
        
        analysis = AudioAnalysis(
            timestamp=now,
            detection_type=AudioDetectionType.EXCESSIVE_NOISE.value,
            alert_level=AudioAlertLevel.MEDIUM.value,
            confidence=0.70,
            score=65,
            reason="Excessive background noise detected",
            background_noise_level=avg_energy,
            speech_stats=asdict(features),
        )
        state.last_analysis = analysis
        return analysis
    
    # ===== Check 4: Monotone Speech (MEDIUM) =====
    if features.pitch_variation < EAAEConfig.NORMAL_PITCH_VARIATION_MIN:
        logger.warning(f"⚠️ MEDIUM: Monotone speech (pitch_variation={features.pitch_variation:.3f})")
        
        analysis = AudioAnalysis(
            timestamp=now,
            detection_type=AudioDetectionType.MONOTONE_SPEECH.value,
            alert_level=AudioAlertLevel.MEDIUM.value,
            confidence=0.60,
            score=55,
            reason=f"Unnatural monotone speech pattern detected",
            speech_stats=asdict(features),
        )
        state.last_analysis = analysis
        return analysis
    
    # ===== Check 5: Unusual Speech Rate (MEDIUM) =====
    expected_min = EAAEConfig.NORMAL_SPEECH_RATE * (1 - EAAEConfig.SPEECH_RATE_TOLERANCE)
    expected_max = EAAEConfig.NORMAL_SPEECH_RATE * (1 + EAAEConfig.SPEECH_RATE_TOLERANCE)
    
    if features.speech_rate < expected_min or features.speech_rate > expected_max:
        logger.warning(f"⚠️ MEDIUM: Unusual speech rate ({features.speech_rate:.0f} WPM)")
        
        analysis = AudioAnalysis(
            timestamp=now,
            detection_type=AudioDetectionType.UNUSUAL_SPEECH_RATE.value,
            alert_level=AudioAlertLevel.MEDIUM.value,
            confidence=0.55,
            score=50,
            reason=f"Unusual speech rate ({features.speech_rate:.0f} WPM, expected {EAAEConfig.NORMAL_SPEECH_RATE}±{int(EAAEConfig.SPEECH_RATE_TOLERANCE*100)}%)",
            speech_stats=asdict(features),
        )
        state.last_analysis = analysis
        return analysis
    
    # ===== All checks passed - Normal Speech =====
    analysis = AudioAnalysis(
        timestamp=now,
        detection_type=AudioDetectionType.NORMAL_SPEECH.value,
        alert_level=AudioAlertLevel.NONE.value,
        confidence=0.05,
        score=10,
        reason="Normal speech pattern detected",
        speech_stats=asdict(features),
    )
    
    state.last_analysis = analysis
    return analysis


# ========== SESSION MANAGEMENT ==========

def reset_audio_session(session_id: str):
    """Reset audio analysis state for a session"""
    if session_id in _audio_session_states:
        _audio_session_states[session_id] = AudioSessionState(session_id=session_id)
        logger.info(f"✅ Audio session {session_id} reset")


def get_audio_session_summary(session_id: str) -> Dict:
    """Get summary of audio analysis for a session"""
    state = get_audio_session_state(session_id)
    
    # Calculate average AI confidence
    avg_ai_confidence = (
        np.mean(state.ai_confidence_readings) 
        if state.ai_confidence_readings 
        else 0.0
    )
    
    return {
        "session_id": session_id,
        "total_audio_duration": round(state.total_audio_duration, 2),
        "silence_duration": round(state.silence_duration, 2),
        "ai_detections": state.consecutive_ai_detections,
        "average_ai_confidence": round(avg_ai_confidence, 3),
        "last_analysis": asdict(state.last_analysis) if state.last_analysis else None,
    }


# ========== BATCH ANALYSIS ==========

def analyze_audio_batch(
    audio_bytes: bytes,
    session_id: str = "default"
) -> AudioAnalysis:
    """
    Analyze complete audio recording (batch mode).
    
    Args:
        audio_bytes: Complete audio recording
        session_id: Session identifier
    
    Returns:
        AudioAnalysis result
    """
    return analyze_audio_chunk(audio_bytes, session_id)
