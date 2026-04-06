"""
Audio Feature Extraction for Speech Authenticity Detection
"""

import numpy as np
import logging
from typing import Dict

logger = logging.getLogger(__name__)

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa not available - audio feature analysis limited")

try:
    from app.config import authenticity_config as config
except ImportError:
    class FallbackConfig:
        ENABLED = True
        AUDIO_FEATURE_ANALYSIS = True
        MONOTONE_THRESHOLD = 0.6
    config = FallbackConfig()


class AudioFeaturesExtractor:
    """Extracts audio features for authenticity detection"""
    
    def __init__(self):
        self.sample_rate = 16000
    
    def extract_features(self, audio_bytes: bytes) -> Dict:
        if not getattr(config, 'ENABLED', True) or not getattr(config, 'AUDIO_FEATURE_ANALYSIS', True):
            return self._empty_result()
        
        if not LIBROSA_AVAILABLE:
            return self._basic_analysis(audio_bytes)
        
        try:
            audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
            
            if len(audio_array) < self.sample_rate:
                return self._empty_result()
            
            pitch_features = self._analyze_pitch(audio_array)
            energy_features = self._analyze_energy(audio_array)
            pause_features = self._analyze_pauses(audio_array)
            speech_rate = self._estimate_speech_rate(audio_array)
            
            reading_score = self._calculate_reading_score(
                pitch_features, energy_features, pause_features
            )
            
            result = {
                "pitch_mean": round(pitch_features["mean"], 2),
                "pitch_std": round(pitch_features["std"], 2),
                "pitch_variation": round(pitch_features["variation"], 3),
                "energy_mean": round(energy_features["mean"], 4),
                "energy_std": round(energy_features["std"], 4),
                "pause_count": pause_features["count"],
                "pause_ratio": round(pause_features["ratio"], 3),
                "speech_rate": round(speech_rate, 2),
                "reading_score": round(reading_score, 3),
                "is_monotone": pitch_features["variation"] < getattr(config, 'MONOTONE_THRESHOLD', 0.6),
                "confidence": 0.8
            }
            
            return result
        except Exception as e:
            logger.error(f"Audio feature extraction error: {e}", exc_info=True)
            return self._empty_result()
    
    def _basic_analysis(self, audio_bytes: bytes) -> Dict:
        try:
            audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
            energy = np.sqrt(np.mean(audio_array ** 2))
            variation = np.std(audio_array) / (np.mean(np.abs(audio_array)) + 1e-6)
            
            return {
                "pitch_mean": 0.0,
                "pitch_std": 0.0,
                "pitch_variation": float(variation),
                "energy_mean": float(energy),
                "energy_std": 0.0,
                "pause_count": 0,
                "pause_ratio": 0.0,
                "speech_rate": 0.0,
                "reading_score": 0.5,
                "is_monotone": variation < 0.3,
                "confidence": 0.5
            }
        except:
            return self._empty_result()
    
    def _analyze_pitch(self, audio: np.ndarray) -> Dict:
        try:
            pitches, magnitudes = librosa.piptrack(y=audio, sr=self.sample_rate, fmin=75, fmax=400)
            
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if not pitch_values:
                return {"mean": 0, "std": 0, "variation": 0}
            
            pitch_array = np.array(pitch_values)
            mean = np.mean(pitch_array)
            std = np.std(pitch_array)
            variation = std / (mean + 1e-6)
            
            return {"mean": float(mean), "std": float(std), "variation": float(variation)}
        except Exception as e:
            return {"mean": 0, "std": 0, "variation": 0}
    
    def _analyze_energy(self, audio: np.ndarray) -> Dict:
        try:
            rms = librosa.feature.rms(y=audio)[0]
            return {"mean": float(np.mean(rms)), "std": float(np.std(rms))}
        except:
            return {"mean": 0, "std": 0}
    
    def _analyze_pauses(self, audio: np.ndarray) -> Dict:
        try:
            rms = librosa.feature.rms(y=audio, frame_length=2048, hop_length=512)[0]
            threshold = np.mean(rms) * 0.3
            is_pause = rms < threshold
            pause_count = np.sum(np.diff(is_pause.astype(int)) == 1)
            pause_ratio = float(np.sum(is_pause) / len(is_pause))
            return {"count": int(pause_count), "ratio": pause_ratio}
        except:
            return {"count": 0, "ratio": 0}
    
    def _estimate_speech_rate(self, audio: np.ndarray) -> float:
        try:
            rms = librosa.feature.rms(y=audio, frame_length=2048, hop_length=512)[0]
            threshold = np.mean(rms) * 0.6
            peaks = np.where(rms > threshold)[0]
            
            if len(peaks) > 0:
                peak_groups = np.split(peaks, np.where(np.diff(peaks) > 5)[0] + 1)
                syllable_count = len(peak_groups)
            else:
                syllable_count = 0
            
            duration = len(audio) / self.sample_rate / 60
            words_per_minute = (syllable_count / 1.5) / max(duration, 0.01)
            return float(words_per_minute)
        except:
            return 0.0
    
    def _calculate_reading_score(self, pitch: Dict, energy: Dict, pause: Dict) -> float:
        monotone_score = 1.0 - min(pitch["variation"] / 0.3, 1.0)
        energy_consistency = 1.0 - min(energy["std"] / (energy["mean"] + 1e-6), 1.0)
        
        pause_score = 0.5
        if pause["count"] < 2:
            pause_score = 0.8
        elif pause["count"] > 6:
            pause_score = 0.6
        else:
            pause_score = 0.2
        
        reading_score = (monotone_score * 0.4 + energy_consistency * 0.3 + pause_score * 0.3)
        return min(reading_score, 1.0)
    
    def _empty_result(self) -> Dict:
        return {
            "pitch_mean": 0.0,
            "pitch_std": 0.0,
            "pitch_variation": 0.0,
            "energy_mean": 0.0,
            "energy_std": 0.0,
            "pause_count": 0,
            "pause_ratio": 0.0,
            "speech_rate": 0.0,
            "reading_score": 0.0,
            "is_monotone": False,
            "confidence": 0.0
        }


_audio_extractor = None

def get_audio_extractor() -> AudioFeaturesExtractor:
    global _audio_extractor
    if _audio_extractor is None:
        _audio_extractor = AudioFeaturesExtractor()
        logger.info("✅ Audio features extractor initialized")
    return _audio_extractor