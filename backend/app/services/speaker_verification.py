def verify_speaker(audio_data, sample_rate, last_embedding):
    try:
        # TODO: replace with real speaker verification logic
        same_speaker = True
        confidence = 0.0
        embedding = None  # numpy / torch allowed here (not returned)

        result = {
            "same_speaker": bool(same_speaker),
            "confidence": float(confidence),
            "status": "ok"
        }

        return result, embedding

    except Exception as e:
        return {
            "same_speaker": True,
            "confidence": 0.0,
            "status": "error",
            "error": str(e)
        }, None
