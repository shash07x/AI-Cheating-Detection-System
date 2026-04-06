import numpy as np
import librosa
import time

# ---------------------------------------
# WHISPER / PROMPTED SPEECH DETECTION
# ---------------------------------------

# persistent state (safe, lightweight)
_last_whisper_time = None
_whisper_start = None

# thresholds (tuned for interviews)
MIN_RMS = 0.012
HIGH_CENTROID = 3200
LOW_HARMONIC_ENERGY = 0.015

MIN_WHISPER_DURATION = 0.8   # seconds (ignore brief moments)
MAX_CONFIDENCE = 100


def detect_whisper(audio_np, sr=16000):
    """
    Detects suspicious whisper / coached speech patterns.
    NOT normal low-volume speaking.

    Returns:
      {
        is_whisper: bool,
        confidence: 0–100,
        reasons: list,
        status: str
      }
    """

    global _last_whisper_time, _whisper_start

    try:
        if audio_np is None or len(audio_np) < 1000:
            return {
                "is_whisper": False,
                "confidence": 0,
                "reasons": [],
                "status": "audio_too_short"
            }

        # normalize safely
        audio_np = audio_np / (np.max(np.abs(audio_np)) + 1e-9)

        now = time.time()

        # ---------------- FEATURES ----------------
        rms = float(np.mean(librosa.feature.rms(y=audio_np)))
        centroid = float(np.mean(
            librosa.feature.spectral_centroid(y=audio_np, sr=sr)
        ))

        harmonic, _ = librosa.effects.hpss(audio_np)
        harmonic_energy = float(np.mean(np.abs(harmonic)))

        confidence = 0
        reasons = []

        # ---------------- RULE 1: SOFT + BREATHY ----------------
        whisper_like = (
            rms < MIN_RMS and
            centroid > HIGH_CENTROID and
            harmonic_energy < LOW_HARMONIC_ENERGY
        )

        # ---------------- TEMPORAL CHECK ----------------
        if whisper_like:
            if _whisper_start is None:
                _whisper_start = now
                return {
                    "is_whisper": False,
                    "confidence": 20,
                    "reasons": ["Possible low-energy speech"],
                    "status": "starting"
                }

            duration = now - _whisper_start

            if duration >= MIN_WHISPER_DURATION:
                confidence = 60 + int(min(40, duration * 20))
                reasons.append("Sustained low-energy coached speech detected")

        else:
            _whisper_start = None
            _last_whisper_time = now
            return {
                "is_whisper": False,
                "confidence": 0,
                "reasons": [],
                "status": "normal"
            }

        confidence = min(MAX_CONFIDENCE, confidence)

        return {
            "is_whisper": confidence >= 60,
            "confidence": confidence,
            "reasons": reasons,
            "status": "ok"
        }

    except Exception as e:
        return {
            "is_whisper": False,
            "confidence": 0,
            "reasons": [],
            "status": "error",
            "error": str(e)
        }
