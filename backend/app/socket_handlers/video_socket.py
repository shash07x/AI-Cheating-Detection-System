import base64
import cv2
import numpy as np
from collections import defaultdict, deque

from app.extensions import socketio
from app.services.video_analyzer import analyze_face
from app.services.eye_gaze_tracking import analyze_gaze
from app.services.fraud_aggregator import aggregate_scores, explain

# ---------------------------------------
# REAL-TIME SESSION STATE (PER SESSION)
# ---------------------------------------

SESSION_VIDEO_STATE = defaultdict(lambda: {
    "scores": deque(maxlen=12)  # rolling window (~18s)
})


@socketio.on("video_frame")
def handle_video_frame(data):
    try:
        session_id = data.get("session_id", "demo_session_01")
        frame_b64 = data.get("frame")

        if not frame_b64:
            return
        

        # ---------------------------------------
        # Decode base64 -> OpenCV image
        # ---------------------------------------
        try:
            header, encoded = frame_b64.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except Exception:
            return

        if frame is None or frame.size == 0:
            return

        # ---------------------------------------
        # REAL VIDEO ANALYSIS
        # ---------------------------------------
        face_score = analyze_face(frame)       # 0–100
        gaze_score = analyze_gaze(frame)       # 0–100

        # Weighted video score
        video_score = int((face_score * 0.6) + (gaze_score * 0.4))

        state = SESSION_VIDEO_STATE[session_id]
        state["scores"].append(video_score)

        avg_video_score = int(
            sum(state["scores"]) / len(state["scores"])
        )
        

        # ---------------------------------------
        # AGGREGATION (VIDEO ONLY HERE)
        # ---------------------------------------
        agg = aggregate_scores(
            video_score=avg_video_score,
            audio_score=0,
            tab_switches=0
        )

        explanation = explain(
            video_score=avg_video_score,
            audio_score=0
        )

        # ---------------------------------------
        # EMIT REAL-TIME ALERT
        # ---------------------------------------
        socketio.emit("fraud_alert", {
            "session_id": session_id,
            "video_score": avg_video_score,
            "audio_score": 0,
            "final_score": agg["final_score"],
            "violation_level": agg["violation_level"],
            "confidence": explanation["confidence"],
            "reasons": explanation["reasons"],
        })
        

    except Exception as e:
        print("Video socket error:", e)
