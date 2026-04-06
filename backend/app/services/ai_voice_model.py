import os
import numpy as np
import logging

logger = logging.getLogger(__name__)

# ----------------------------------------
# CONSTANTS
# ----------------------------------------

TARGET_SAMPLE_RATE = 16000
MAX_DURATION_SEC = 3
MAX_LEN = TARGET_SAMPLE_RATE * MAX_DURATION_SEC


# ----------------------------------------
# FEATURE EXTRACTION (No Librosa Required)
# ----------------------------------------

def extract_audio_features(audio_np):
    """
    Extract audio features for AI detection without ML models
    
    Returns dict with:
        - pitch_variance
        - zero_crossing_rate
        - rms_energy
        - spectral_flatness
        - amplitude_consistency
    """
    try:
        # Ensure float32
        audio_np = audio_np.astype(np.float32)
        
        # 1. RMS Energy
        rms = float(np.sqrt(np.mean(audio_np ** 2)))
        
        # 2. Pitch Variance (frequency domain variance)
        pitch_variance = float(np.var(audio_np))
        
        # 3. Zero Crossing Rate
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_np))))
        zcr = float(zero_crossings / len(audio_np))
        
        # 4. Dynamic Range
        dynamic_range = float(np.max(np.abs(audio_np)) - np.min(np.abs(audio_np)))
        
        # 5. Amplitude Consistency (Standard deviation of RMS over windows)
        window_size = 1600  # 100ms windows at 16kHz
        num_windows = len(audio_np) // window_size
        
        if num_windows > 2:
            window_rms = []
            for i in range(num_windows):
                start = i * window_size
                end = start + window_size
                window_rms.append(np.sqrt(np.mean(audio_np[start:end] ** 2)))
            
            amplitude_consistency = float(np.std(window_rms))
        else:
            amplitude_consistency = 0.0
        
        # 6. High Frequency Content (Simple approximation)
        diff = np.diff(audio_np)
        high_freq_energy = float(np.sqrt(np.mean(diff ** 2)))
        
        return {
            "rms": rms,
            "pitch_variance": pitch_variance,
            "zcr": zcr,
            "dynamic_range": dynamic_range,
            "amplitude_consistency": amplitude_consistency,
            "high_freq_energy": high_freq_energy
        }
    
    except Exception as e:
        logger.error(f"Feature extraction error: {e}")
        return None


# ----------------------------------------
# AI VOICE DETECTION (HEURISTIC-BASED)
# ----------------------------------------

def detect_ai_voice(audio_input):
    """
    Detects AI-generated voice using heuristic audio analysis
    
    Accepts:
      - raw audio bytes (from socket)
      - OR numpy waveform array
    
    Returns:
      dict with keys:
        is_ai, confidence, reasons
    """
    
    try:
        # ----------------------------------------
        # Convert bytes to numpy if needed
        # ----------------------------------------
        if isinstance(audio_input, (bytes, bytearray)):
            try:
                # Try int16 first (most common)
                audio_np = np.frombuffer(audio_input, dtype=np.int16)
                audio_np = audio_np.astype(np.float32) / 32768.0
            except Exception:
                try:
                    # Try float32
                    audio_np = np.frombuffer(audio_input, dtype=np.float32)
                except Exception as e:
                    logger.error(f"Audio decode error: {e}")
                    return {
                        "is_ai": False,
                        "confidence": 0,
                        "reasons": ["Audio decode failed"]
                    }
        else:
            audio_np = np.array(audio_input, dtype=np.float32)
        
        # ----------------------------------------
        # Validate audio
        # ----------------------------------------
        if audio_np is None or len(audio_np) < 2000:
            return {
                "is_ai": False,
                "confidence": 0,
                "reasons": ["Audio too short"]
            }
        
        # ----------------------------------------
        # Normalize audio
        # ----------------------------------------
        max_amp = np.max(np.abs(audio_np))
        if max_amp > 0:
            audio_np = audio_np / max_amp
        
        # Trim to max length
        if len(audio_np) > MAX_LEN:
            audio_np = audio_np[:MAX_LEN]
        
        # ----------------------------------------
        # Extract features
        # ----------------------------------------
        features = extract_audio_features(audio_np)
        
        if features is None:
            return {
                "is_ai": False,
                "confidence": 0,
                "reasons": ["Feature extraction failed"]
            }
        
        # ----------------------------------------
        # AI Detection Heuristics
        # ----------------------------------------
        
        ai_score = 0
        reasons = []
        
        # 1. MONOTONE PITCH (AI voices have very consistent pitch)
        if features["pitch_variance"] < 0.008:
            ai_score += 25
            reasons.append("Monotone pitch (AI indicator)")
        elif features["pitch_variance"] > 0.03:
            reasons.append("Natural pitch variation")
        
        # 2. CONSISTENT ZERO-CROSSING RATE (Synthetic voices are regular)
        if 0.06 < features["zcr"] < 0.14:
            ai_score += 20
            reasons.append("Synthetic voice pattern")
        elif features["zcr"] > 0.2:
            reasons.append("Natural voice patterns")
        
        # 3. AMPLITUDE CONSISTENCY (AI is too consistent)
        if features["amplitude_consistency"] < 0.015:
            ai_score += 20
            reasons.append("Robotic amplitude consistency")
        
        # 4. LIMITED DYNAMIC RANGE (AI voices lack natural dynamics)
        if features["dynamic_range"] < 0.7:
            ai_score += 15
            reasons.append("Limited dynamic range")
        
        # 5. RMS ENERGY TOO CONSISTENT (Real speech fluctuates more)
        if 0.08 < features["rms"] < 0.22:
            ai_score += 10
            reasons.append("Consistent energy levels")
        
        # 6. HIGH FREQUENCY CONTENT (AI lacks natural breathiness)
        if features["high_freq_energy"] < 0.05:
            ai_score += 10
            reasons.append("Lack of natural high frequencies")
        
        # ----------------------------------------
        # Final scoring
        # ----------------------------------------
        
        # Conservative threshold (important to avoid false positives)
        confidence = min(ai_score, 100)
        is_ai = confidence >= 70  # 70% threshold
        
        # Add summary reason
        if is_ai:
            summary = f"AI-generated voice detected ({confidence}%)"
        else:
            summary = f"Human speech pattern ({100-confidence}% human)"
        
        reasons.insert(0, summary)
        
        logger.debug(f"AI Detection - Score: {confidence}%, Features: {features}")
        
        return {
            "is_ai": is_ai,
            "confidence": confidence,
            "reasons": reasons[:4]  # Top 4 reasons
        }
    
    except Exception as e:
        logger.error(f"AI voice detection error: {e}", exc_info=True)
        return {
            "is_ai": False,
            "confidence": 0,
            "reasons": [f"Detection failed: {str(e)}"]
        }


# ----------------------------------------
# BATCH DETECTION (For multiple chunks)
# ----------------------------------------

def detect_ai_voice_batch(audio_chunks):
    """
    Analyze multiple audio chunks and return average confidence
    
    Args:
        audio_chunks: list of audio arrays
        
    Returns:
        dict with aggregated results
    """
    results = []
    
    for chunk in audio_chunks:
        result = detect_ai_voice(chunk)
        results.append(result)
    
    if not results:
        return {
            "is_ai": False,
            "confidence": 0,
            "reasons": ["No audio chunks"]
        }
    
    # Average confidence
    avg_confidence = int(np.mean([r["confidence"] for r in results]))
    
    # Majority vote for is_ai
    ai_count = sum(1 for r in results if r["is_ai"])
    is_ai = ai_count > len(results) / 2
    
    # Collect all reasons
    all_reasons = []
    for r in results:
        all_reasons.extend(r.get("reasons", []))
    
    # Get unique reasons
    unique_reasons = list(set(all_reasons))[:4]
    
    return {
        "is_ai": is_ai,
        "confidence": avg_confidence,
        "reasons": unique_reasons,
        "chunks_analyzed": len(results),
        "ai_chunks": ai_count
    }