def compute_ai_percentage(audio, video, linguistic):

    # weighted fusion
    ai = (
        audio * 0.4 +
        linguistic * 0.4 +
        video * 0.2
    )

    ai = min(100, int(ai))

    return {
        "ai": ai,
        "human": 100 - ai
    }