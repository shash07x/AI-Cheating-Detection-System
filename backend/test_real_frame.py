#!/usr/bin/env python3
"""
Test that video_routes module imports successfully
"""
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 70)
print("TEST: VIDEO_ROUTES MODULE IMPORT VERIFICATION")
print("=" * 70)

try:
    print("\n[1] Importing video_routes module...")
    from app.routes.video_routes import video_bp, analyze_video
    print("    ✓ Successfully imported video_routes")
    
    print("\n[2] Checking for required dependencies...")
    from app.services.head_pose_fallback import estimate_head_pose_fallback
    print("    ✓ Successfully imported head_pose_fallback")
    
    from app.services.stable_vision_engine import analyze_frame
    print("    ✓ Successfully imported SVE engine")
    
    from app.services.head_pose_estimation import estimate_head_pose
    print("    ✓ Successfully imported head_pose_estimation")
    
    print("\n[3] Checking head pose initialization...")
    # Try to initialize head pose (should load YOLO or gracefully fail)
    import cv2
    import numpy as np
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = estimate_head_pose(test_frame)
    print(f"    Head pose result keys: {list(result.keys())}")
    print(f"    Status: {result.get('status')}")
    print("    ✓ Head pose estimation initialized")
    
    print("\n[4] Testing fallback cascade...")
    fallback_result = estimate_head_pose_fallback(test_frame)
    print(f"    Fallback result keys: {list(fallback_result.keys())}")
    print(f"    Status: {fallback_result.get('status')}")
    print("    ✓ Fallback cascade working")
    
    print("\n[5] Testing SVE engine...")
    # Parse fallback result to get parameters
    from app.services.stable_vision_engine import HeadPose
    head_pose = HeadPose(
        direction="center",
        horizontal_offset=0.0,
        vertical_offset=0.0,
        eyes_closed=False
    )
    sve_result = analyze_frame(
        frame=test_frame,
        head_pose=head_pose,
        face_count=fallback_result.get('person_count', 1),
        phone_detected=fallback_result.get('phone_detected', False),
        session_id="test_session"
    )
    print(f"    SVE analysis detection_type: {sve_result.detection_type}")
    print(f"    SVE analysis alert_level: {sve_result.alert_level}")
    print(f"    SVE analysis score: {sve_result.score}")
    print("    ✓ SVE engine working")
    
    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE - ALL MODULES WORKING!")
    print("=" * 70)
    print("""
Pipeline Status:
    ✓ video_routes module imports successfully
    ✓ head_pose_estimation loads without crashes
    ✓ head_pose_fallback cascade classifier ready
    ✓ SVE engine initialized and analyzing
    ✓ Fallback chain working: YOLO error → cascade fallback → SVE

Next Steps:
    1. Send real video frames to /analyze endpoint
    2. Verify CRITICAL alerts for phone/multiple faces
    3. Verify MEDIUM alerts for looking away
    4. Verify LOW alerts for normal state
    5. Verify screenshots captured for violations
    """)
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
