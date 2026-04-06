"""Simulate candidate audio sending and verify dashboard receives it"""
import socketio
import time
import base64
import numpy as np
import json

# Create Socket.IO client simulating the candidate
candidate = socketio.Client()
interviewer = socketio.Client()

results = {"audio_received": False, "risk_received": False, "video_ok": False}

@interviewer.on("ai_live_update")
def on_ai_update(data):
    results["audio_received"] = True
    print(f"  DASHBOARD got ai_live_update: score={data.get('ai_score')}, status={data.get('status')}")

@interviewer.on("risk_update")
def on_risk(data):
    results["risk_received"] = True
    print(f"  DASHBOARD got risk_update: video={data.get('video_score')}, audio={data.get('audio_score')}, level={data.get('violation_level')}")

@interviewer.on("fraud_alert")
def on_fraud(data):
    print(f"  DASHBOARD got fraud_alert: {data.get('violation_level')}")

print("=" * 55)
print("  END-TO-END AUDIO/VIDEO DETECTION TEST")
print("=" * 55)

# Connect both clients
print("\n[1] Connecting clients...")
candidate.connect("http://127.0.0.1:5000", transports=["polling"])
interviewer.connect("http://127.0.0.1:5000", transports=["polling"])
print(f"  Candidate SID: {candidate.sid}")
print(f"  Interviewer SID: {interviewer.sid}")

# Register roles
candidate.emit("register_role", {"session_id": "session_01", "role": "candidate"})
candidate.emit("join_session", {"session_id": "session_01", "role": "candidate"})
interviewer.emit("register_role", {"session_id": "session_01", "role": "interviewer"})
interviewer.emit("join_session", {"session_id": "session_01", "role": "interviewer"})
time.sleep(1)
print("  Roles registered")

# [2] Test Video
print("\n[2] Testing video analysis...")
import requests, cv2
frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
_, buf = cv2.imencode(".jpg", frame)
b64 = base64.b64encode(buf).decode()
r = requests.post("http://127.0.0.1:5000/video/analyze", json={"session_id": "session_01", "frame": b64}, timeout=30)
if r.ok:
    d = r.json()
    results["video_ok"] = True
    print(f"  Video: score={d.get('final_score')}, level={d.get('violation_level')}")
    time.sleep(2)  # Wait for risk_update emission

# [3] Send audio chunks  
print("\n[3] Sending audio chunks (simulating speech)...")
for i in range(4):
    # Generate synthetic speech-like audio (sine wave + noise)
    t = np.linspace(0, 2, 16000 * 2, dtype=np.float32)
    audio = (0.3 * np.sin(2 * np.pi * 440 * t) + 0.05 * np.random.randn(len(t))).astype(np.float32)
    audio_int16 = (audio * 32768).clip(-32768, 32767).astype(np.int16)
    audio_bytes = audio_int16.tobytes()
    audio_b64 = "data:audio/pcm;base64," + base64.b64encode(audio_bytes).decode()
    
    candidate.emit("audio_chunk", {
        "session_id": "session_01",
        "audio": audio_b64
    })
    print(f"  Sent audio chunk {i+1}/4 ({len(audio_bytes)} bytes)")
    time.sleep(3)

# Wait for processing
print("\n[4] Waiting for backend processing...")
time.sleep(10)

# Results
print("\n" + "=" * 55)
print("  RESULTS")
print("=" * 55)
print(f"  Video Detection:   {'PASS' if results['video_ok'] else 'FAIL'}")
print(f"  Audio Received:    {'PASS' if results['audio_received'] else 'FAIL'}")
print(f"  Risk Updates:      {'PASS' if results['risk_received'] else 'FAIL'}")
total = sum(results.values())
print(f"\n  {total}/3 checks passed")
print("=" * 55)

candidate.disconnect()
interviewer.disconnect()
