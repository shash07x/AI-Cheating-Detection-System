"""
Enhanced AI Speech Detection
Combines multiple signals for better accuracy
"""

import numpy as np
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

try:
    import librosa
    LIBROSA_AVAILABLE = True
except:
    LIBROSA_AVAILABLE = False


class EnhancedAIDetector:
    """
    Multi-signal AI speech detection.
    Detects if speech is AI-generated or human reading AI text.
    """
    
    def __init__(self):
        self.sample_rate = 16000
        
        # Thresholds calibrated for better accuracy
        self.thresholds = {
            "filler_ratio_min": 0.015,  # Natural speech has >1.5% filler words
            "pitch_variation_min": 0.35,  # Natural speech varies >35%
            "pause_irregularity_min": 0.3,  # Natural pauses are irregular
            "speech_rate_min": 100,  # Natural: 100-180 WPM
            "speech_rate_max": 200,
            "ai_phrase_weight": 25,  # Each AI phrase adds 25%
        }
    
    def detect(self, audio_bytes: bytes, transcript: str) -> Tuple[int, str]:
        """
        Main detection function.
        
        Returns:
            (ai_percentage: int, explanation: str)
        """
        if not audio_bytes or not transcript:
            return 0, "Insufficient data"
        
        # Skip if transcript is too short (silence or noise)
        if len(transcript) < 10:
            return 0, "Transcript too short (silence/noise)"
        
        # Calculate individual signals
        signals = {}
        
        # 1. Linguistic Analysis
        signals['linguistic'] = self._analyze_text(transcript)
        
        # 2. Audio Feature Analysis
        if LIBROSA_AVAILABLE:
            signals['audio'] = self._analyze_audio(audio_bytes)
        else:
            signals['audio'] = self._basic_audio_analysis(audio_bytes)
        
        # 3. Combined Analysis
        ai_percentage, explanation = self._combine_signals(signals, transcript)
        
        logger.info(
            f"AI Detection: {ai_percentage}% | "
            f"Text: {signals['linguistic']}% | "
            f"Audio: {signals['audio']['score']}% | "
            f"{explanation}"
        )
        
        return ai_percentage, explanation
    
    def _analyze_text(self, text: str) -> int:
        """Analyze text for AI patterns"""
        text_lower = text.lower()
        words = text_lower.split()
        
        if len(words) < 5:
            return 0
        
        score = 0
        
        # AI signature phrases (strong indicators)
        ai_phrases = [
            "first and foremost",
            "it's important to note",
            "it's worth noting",
            "in today's digital age",
            "leverage the power of",
            "dive deep into",
            "at the end of the day",
            "paradigm shift",
            "cutting-edge",
            "revolutionary",
            "game-changer",
            "unlock the potential",
        ]
        
        for phrase in ai_phrases:
            if phrase in text_lower:
                score += self.thresholds["ai_phrase_weight"]
                logger.debug(f"Found AI phrase: '{phrase}'")
        
        # Filler words (natural speech markers)
        filler_words = ["um", "uh", "like", "you know", "so", "well", "actually", "basically"]
        filler_count = sum(1 for word in words if word in filler_words)
        filler_ratio = filler_count / len(words)
        
        if filler_ratio < self.thresholds["filler_ratio_min"]:
            score += 30  # Very few fillers = suspicious
            logger.debug(f"Low filler ratio: {filler_ratio:.3f}")
        
        # Perfect grammar (no contractions)
        contractions = ["'m", "'re", "'ve", "'ll", "'d", "n't"]
        has_contractions = any(c in text for c in contractions)
        if not has_contractions and len(words) > 20:
            score += 15  # Perfect grammar = AI-like
        
        # Sentence structure consistency
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if len(sentences) >= 3:
            lengths = [len(s.split()) for s in sentences]
            variance = np.var(lengths) if len(lengths) > 1 else 100
            if variance < 5:  # Very consistent length = AI
                score += 20
        
        return min(score, 100)
    
    def _analyze_audio(self, audio_bytes: bytes) -> Dict:
        """Analyze audio for AI/reading patterns"""
        try:
            audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
            
            if len(audio_array) < self.sample_rate:
                return {"score": 0, "reasons": ["Audio too short"]}
            
            reasons = []
            score = 0
            
            # 1. Pitch Analysis
            try:
                pitches, magnitudes = librosa.piptrack(
                    y=audio_array,
                    sr=self.sample_rate,
                    fmin=75,
                    fmax=400
                )
                
                pitch_values = []
                for t in range(pitches.shape[1]):
                    index = magnitudes[:, t].argmax()
                    pitch = pitches[index, t]
                    if pitch > 0:
                        pitch_values.append(pitch)
                
                if pitch_values:
                    pitch_std = np.std(pitch_values)
                    pitch_mean = np.mean(pitch_values)
                    pitch_variation = pitch_std / (pitch_mean + 1e-6)
                    
                    if pitch_variation < self.thresholds["pitch_variation_min"]:
                        score += 35
                        reasons.append(f"Monotone (var={pitch_variation:.2f})")
            except Exception as e:
                logger.debug(f"Pitch analysis failed: {e}")
            
            # 2. Pause Analysis
            try:
                rms = librosa.feature.rms(y=audio_array, frame_length=2048, hop_length=512)[0]
                threshold = np.mean(rms) * 0.3
                is_pause = rms < threshold
                
                # Find pause segments
                pause_changes = np.diff(is_pause.astype(int))
                pause_starts = np.where(pause_changes == 1)[0]
                
                if len(pause_starts) > 2:
                    pause_intervals = np.diff(pause_starts)
                    pause_irregularity = np.std(pause_intervals) / (np.mean(pause_intervals) + 1)
                    
                    if pause_irregularity < self.thresholds["pause_irregularity_min"]:
                        score += 25
                        reasons.append("Regular pauses (reading pattern)")
            except Exception as e:
                logger.debug(f"Pause analysis failed: {e}")
            
            # 3. Energy Consistency
            try:
                energy_std = np.std(rms)
                energy_mean = np.mean(rms)
                energy_consistency = 1 - min(energy_std / (energy_mean + 1e-6), 1)
                
                if energy_consistency > 0.7:
                    score += 20
                    reasons.append("Consistent volume (reading)")
            except Exception as e:
                logger.debug(f"Energy analysis failed: {e}")
            
            return {
                "score": min(score, 100),
                "reasons": reasons
            }
            
        except Exception as e:
            logger.error(f"Audio analysis error: {e}")
            return {"score": 0, "reasons": ["Analysis failed"]}
    
    def _basic_audio_analysis(self, audio_bytes: bytes) -> Dict:
        """Fallback when librosa not available"""
        try:
            audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
            
            # Simple RMS variation
            chunk_size = 1600  # 0.1s chunks
            chunks = [audio_array[i:i+chunk_size] for i in range(0, len(audio_array), chunk_size)]
            rms_values = [np.sqrt(np.mean(chunk**2)) for chunk in chunks if len(chunk) > 0]
            
            if rms_values:
                rms_variation = np.std(rms_values) / (np.mean(rms_values) + 1e-6)
                
                if rms_variation < 0.3:
                    return {"score": 40, "reasons": ["Low audio variation"]}
            
            return {"score": 0, "reasons": ["Insufficient features"]}
        except:
            return {"score": 0, "reasons": ["Analysis failed"]}
    
    def _combine_signals(self, signals: Dict, transcript: str) -> Tuple[int, str]:
        """Combine all signals for final detection"""
        
        text_score = signals.get('linguistic', 0)
        audio_data = signals.get('audio', {})
        audio_score = audio_data.get('score', 0)
        audio_reasons = audio_data.get('reasons', [])
        
        # Weighted combination
        # Text is more reliable than audio
        final_score = int((text_score * 0.6) + (audio_score * 0.4))
        
        # Build explanation
        if final_score < 25:
            explanation = "Natural human speech"
        elif final_score < 50:
            explanation = "Possibly reading prepared text"
        elif final_score < 75:
            explanation = "Likely reading AI-generated text"
        else:
            explanation = "Strong AI indicators detected"
        
        # Add specific reasons
        if audio_reasons:
            explanation += f" ({', '.join(audio_reasons[:2])})"
        
        return final_score, explanation


# Singleton
_detector = None

def get_enhanced_detector():
    global _detector
    if _detector is None:
        _detector = EnhancedAIDetector()
    return _detector

# ===============================
# ADVANCED PLAGIARISM FUSION
# ===============================

from app.services.semantic_similarity import compute_similarity
from app.services.burst_fluency import burst_fluency_score
from app.services.entropy import entropy_score
from app.services.repetition import repetition_score


def run_fusion(transcript,
               audio_score,
               linguistic_score,
               delay_score,
               whisper_score):

    if not transcript or len(transcript.split()) < 5:
        return {"ai_percent": 0}

    semantic = compute_similarity(transcript)
    burst = burst_fluency_score(transcript)
    entropy = entropy_score(transcript)
    repetition = repetition_score(transcript)

    ai = (
        audio_score * 0.20 +
        linguistic_score * 0.15 +
        delay_score * 0.10 +
        whisper_score * 0.10 +
        semantic * 0.25 +
        burst * 0.10 +
        entropy * 0.07 +
        repetition * 0.03
    )

    return {"ai_percent": round(min(100, max(0, ai)), 2)}