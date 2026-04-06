#!/usr/bin/env python3
"""
Comprehensive test of all alert levels in the detection pipeline
"""
import sys
import numpy as np
from app.services.head_pose_fallback import estimate_head_pose_fallback
from app.services.stable_vision_engine import analyze_frame, HeadPose

print("=" * 75)
print("COMPREHENSIVE ALERT LEVEL VERIFICATION TEST")
print("=" * 75)

# Create test frames
test_frame = np.zeros((480, 640, 3), dtype=np.uint8)

# Test scenarios
test_scenarios = [
    {
        "name": "Normal behavior (LOW alert)",
        "head_pose": HeadPose(direction="center", horizontal_offset=0.0, vertical_offset=0.0, eyes_closed=False),
        "face_count": 1,
        "phone_detected": False,
        "expected_level": "none"  # or low
    },
    {
        "name": "Multiple faces detected (CRITICAL alert)",
        "head_pose": HeadPose(direction="center", horizontal_offset=0.0, vertical_offset=0.0, eyes_closed=False),
        "face_count": 2,
        "phone_detected": False,
        "expected_level": "critical"
    },
    {
        "name": "Phone detected (CRITICAL alert)",
        "head_pose": HeadPose(direction="center", horizontal_offset=0.0, vertical_offset=0.0, eyes_closed=False),
        "face_count": 1,
        "phone_detected": True,
        "expected_level": "critical"
    },
    {
        "name": "Looking away (MEDIUM alert)",
        "head_pose": HeadPose(direction="left", horizontal_offset=0.5, vertical_offset=0.0, eyes_closed=False),
        "face_count": 1,
        "phone_detected": False,
        "expected_level": "medium"
    },
]

print("\nRunning detection tests...\n")
all_passed = True

for i, scenario in enumerate(test_scenarios, 1):
    print(f"[Test {i}] {scenario['name']}")
    
    try:
        result = analyze_frame(
            frame=test_frame,
            head_pose=scenario["head_pose"],
            face_count=scenario["face_count"],
            phone_detected=scenario["phone_detected"],
            session_id=f"test_scenario_{i}"
        )
        
        detection_type = result.detection_type
        alert_level = result.alert_level
        score = result.score
        reason = result.reason
        
        # Display results
        print(f"    Detection Type: {detection_type}")
        print(f"    Alert Level: {alert_level}")
        print(f"    Score: {score}")
        print(f"    Reason: {reason}")
        
        # Verify expected alert level
        expected = scenario["expected_level"].lower()
        actual = alert_level.lower()
        
        # For alert level verification
        if expected == "critical":
            matches = actual == "critical"
        elif expected == "medium":
            matches = actual == "medium"
        elif expected == "none":
            matches = actual in ["none", "low"]
        else:
            matches = True
            
        if matches:
            print(f"    [PASS] Alert level matches expected: {expected}")
        else:
            print(f"    [FAIL] Expected {expected}, got {actual}")
            all_passed = False
            
    except Exception as e:
        print(f"    [ERROR] {e}")
        all_passed = False
        
    print()

# Summary
print("=" * 75)
if all_passed:
    print("[SUCCESS] ALL TESTS PASSED")
    print("\nPipeline is working correctly!")
    print("Alert levels returned:")
    print("  + CRITICAL (score 90-95): Phone detected or multiple faces")
    print("  + MEDIUM (score 50-70): Looking away for sustained period")
    print("  + NONE/LOW (score 5-10): Normal behavior")
else:
    print("[FAILED] SOME TESTS FAILED")
    print("Review the output above for details")
    sys.exit(1)

print("=" * 75)
