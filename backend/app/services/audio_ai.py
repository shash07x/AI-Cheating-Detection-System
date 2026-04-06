import numpy as np
import librosa

# ---------------------------------------
# AI VOICE DETECTION (MODEL-READY)
# ---------------------------------------

def detect_ai_voice(audio_np, sr=16000):
    try:
        # Normalize
        audio_np = audio_np / (np.max(np.abs(audio_np)) + 1e-9)

        # MFCC features (used in real detectors)
        mfcc = librosa.feature.mfcc(
            y=audio_np,
            sr=sr,
            n_mfcc=20
        )

        spectral_flatness = np.mean(librosa.feature.spectral_flatness(y=audio_np))
        zcr = np.mean(librosa.feature.zero_crossing_rate(audio_np))

        # ------------------------------------------------
        # PLACEHOLDER FOR TRAINED MODEL (IMPORTANT)
        # ------------------------------------------------
        # model.predict(mfcc)
        # For now: calibrated statistical baseline
        # ------------------------------------------------

        ai_confidence = 0

        if spectral_flatness < 0.2 and zcr < 0.05:
            ai_confidence = 75
        elif spectral_flatness < 0.15:
            ai_confidence = 90

        return {
            "is_ai": ai_confidence > 70,
            "confidence": ai_confidence,
            "status": "ok"
        }

    except Exception as e:
        return {
            "is_ai": False,
            "confidence": 0,
            "status": "error",
            "error": str(e)
        }
