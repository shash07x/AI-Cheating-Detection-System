import numpy as np
import librosa
import io
from collections import deque
import time

# ---------------------------------------
# THRESHOLDS (tunable later)
# ---------------------------------------
SILENCE_RMS_THRESHOLD = 0.01
LOUD_RMS_THRESHOLD = 0.3

# ---------------------------------------
# STATE (smooth across chunks)
# ---------------------------------------
_recent_audio_scores = deque(maxlen=6)
_last_audio_time = None


# ---------------------------------------
# EXISTING FUNCTION (UNCHANGED)
# ---------------------------------------
def analyze_audio(audio_bytes: bytes):
    """
    Batch-style audio analysis (offline / future use)
    """
    reasons = []
    score = 0

    try:
        y, sr = librosa.load(
            io.BytesIO(audio_bytes),
            sr=None,
            mono=True
        )

        if len(y) == 0:
            return 0, []

        rms = np.mean(librosa.feature.rms(y=y))

        if rms < SILENCE_RMS_THRESHOLD:
            score = 20
            reasons.append("Prolonged silence detected")

        elif rms > LOUD_RMS_THRESHOLD:
            score = 50
            reasons.append("Unusual loud audio detected")

        else:
            score = 10

    except Exception as e:
        print("Audio analysis error:", e)
        return 0, []

    return score, reasons


# =========================================================
# REAL-TIME AUDIO ANALYSIS (SOCKET)
# =========================================================
def analyze_audio_chunk(audio_bytes: bytes):
    """
    Real-time audio chunk analysis
    Used by: socket_handlers/audio_socket.py

    Returns:
      score (0–100), reasons (list)
    """

    global _last_audio_time

    try:
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)

        if audio_np.size == 0:
            return 0, []

        audio_float = audio_np.astype(np.float32) / 32768.0
        rms = np.sqrt(np.mean(audio_float ** 2))

        now = time.time()
        _last_audio_time = now

        # -----------------------------
        # SILENCE
        # -----------------------------
        if rms < SILENCE_RMS_THRESHOLD:
            score = 40
            reasons = ["Prolonged silence detected"]

        # -----------------------------
        # LOUD / BACKGROUND
        # -----------------------------
        elif rms > LOUD_RMS_THRESHOLD:
            score = 70
            reasons = ["Unusual loud audio / background voices"]

        # -----------------------------
        # NORMAL SPEECH (BASELINE)
        # -----------------------------
        else:
            score = 10
            reasons = []

        # -----------------------------
        # SMOOTHING
        # -----------------------------
        _recent_audio_scores.append(score)
        avg_score = int(sum(_recent_audio_scores) / len(_recent_audio_scores))

        return avg_score, reasons

    except Exception as e:
        print("Audio chunk analysis error:", e)
        return 0, []
