from app.extensions import socketio
from app.services.fusion_state import update_tab, get_state
from app.services.fraud_aggregator import aggregate_scores, explain

@socketio.on("tab_switch")
def handle_tab(data):
    session_id = data.get("session_id", "demo_session_01")

    update_tab(session_id)
    state = get_state(session_id)

    agg = aggregate_scores(
        state["video_score"],
        state["audio_score"],
        state["tab_switches"]
    )

    explanation = explain(
        state["video_score"],
        state["audio_score"]
    )

    socketio.emit("fraud_alert", {
        "session_id": session_id,
        "video_score": state["video_score"],
        "audio_score": state["audio_score"],
        "final_score": agg["final_score"],
        "violation_level": agg["violation_level"],
        "confidence": explanation["confidence"],
        "reasons": explanation["reasons"],
    })
