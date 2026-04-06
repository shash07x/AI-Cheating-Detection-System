"""Comprehensive project test"""
import requests, json, time

print("=" * 50)
print("COMPREHENSIVE PROJECT TEST")
print("=" * 50)

passed = 0
failed = 0

def test(num, name, func):
    global passed, failed
    try:
        result = func()
        print(f"  [{num}] {name}: PASS - {result}")
        passed += 1
    except Exception as e:
        print(f"  [{num}] {name}: FAIL - {e}")
        failed += 1

# Test 1
def t1():
    r = requests.get("http://127.0.0.1:5000/health", timeout=5)
    return r.json()["status"]
test(1, "Backend Health", t1)

# Test 2
def t2():
    r = requests.get("http://localhost:3000", timeout=5)
    return f"HTTP {r.status_code}"
test(2, "Dashboard (3000)", t2)

# Test 3
def t3():
    r = requests.get("http://localhost:3002", timeout=5)
    return f"HTTP {r.status_code}"
test(3, "Candidate (3002)", t3)

# Test 4
def t4():
    r = requests.post("http://127.0.0.1:5000/ai/start", json={"session_id": "session_01"}, timeout=5)
    return r.json().get("status")
test(4, "/ai/start", t4)

# Test 5
def t5():
    import base64, numpy as np, cv2
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
    _, buf = cv2.imencode(".jpg", frame)
    b64 = base64.b64encode(buf).decode()
    r = requests.post("http://127.0.0.1:5000/video/analyze", json={"session_id":"session_01","frame":b64}, timeout=30)
    d = r.json()
    return f"score={d.get('final_score')}, level={d.get('violation_level')}"
test(5, "Video Analysis", t5)

# Test 6
def t6():
    r = requests.post("http://127.0.0.1:5000/audio/detect-ai", json={"text":"I think um basically the code was like kind of broken you know","session_id":"test"}, timeout=10)
    d = r.json()
    return f"score={d.get('ai_score')}, verdict={d.get('verdict')}"
test(6, "Human Text Detect", t6)

# Test 7
def t7():
    r = requests.post("http://127.0.0.1:5000/audio/detect-ai", json={"text":"Furthermore it is imperative to note that the comprehensive implementation methodology leverages robust frameworks to optimize scalability.","session_id":"test2"}, timeout=10)
    d = r.json()
    return f"score={d.get('ai_score')}, verdict={d.get('verdict')}, source={d.get('source')}"
test(7, "AI Text Detect", t7)

# Test 8
def t8():
    r = requests.get("http://127.0.0.1:5000/ai/health", timeout=5)
    return r.json().get("status")
test(8, "AI Health", t8)

# Test 9
def t9():
    r = requests.get("http://127.0.0.1:5000/socket.io/?transport=polling&EIO=4", timeout=5)
    return f"HTTP {r.status_code}"
test(9, "Socket.IO Polling", t9)

# Test 10
def t10():
    r = requests.post("http://127.0.0.1:5000/session/create", json={"session_id": "session_01"}, timeout=5)
    return f"HTTP {r.status_code}"
test(10, "Session Create", t10)

print()
print("=" * 50)
print(f"RESULTS: {passed} PASSED, {failed} FAILED")
print("=" * 50)
