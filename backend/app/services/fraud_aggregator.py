def aggregate_scores(video_score, audio_score, tab_switches):
    # Normalize tab switches into score
    tab_score = min(tab_switches * 15, 100)

    # Final score (weighted)
    final_score = int(
        (video_score * 0.5) +
        (audio_score * 0.3) +
        (tab_score * 0.2)
    )

    # Violation level
    if final_score >= 85:
        level = "critical"
    elif final_score >= 65:
        level = "high"
    elif final_score >= 40:
        level = "medium"
    else:
        level = "low"

    # 🔑 CONTRIBUTION BREAKDOWN
    total = video_score + audio_score + tab_score or 1

    contributions = {
        "video": int((video_score / total) * 100),
        "audio": int((audio_score / total) * 100),
        "tab": int((tab_score / total) * 100),
    }

    primary_reason = max(contributions, key=contributions.get)

    return {
        "final_score": final_score,
        "violation_level": level,
        "contributions": contributions,
        "primary_reason": primary_reason,
    }


def explain(video_score: int, audio_score: int):
    """
    Generates confidence % and human-readable explanation
    """

    confidence = int(
        min(100, max(10, (video_score * 0.5) + (audio_score * 0.5)))
    )

    reasons = []

    if video_score < 60:
        reasons.append("Irregular face or eye movement detected")
    if audio_score > 60:
        reasons.append("Voice patterns suggest external assistance")

    if not reasons:
        reasons.append("No suspicious patterns detected")

    return {
        "confidence": confidence,
        "reasons": reasons
    }
