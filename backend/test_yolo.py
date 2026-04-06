#!/usr/bin/env python
"""
Test YOLO loading and detection
"""

import sys
import os
import cv2
import numpy as np

sys.path.insert(0, 'c:/Projects/ai-cheating-detection/backend')

print("🔍 Testing YOLO Loading...\n")

try:
    print("1️⃣ Importing ultralytics...")
    from ultralytics import YOLO
    print("   ✅ ultralytics imported")
    
    print("\n2️⃣ Loading YOLO model...")
    model = YOLO('yolov8n-pose.pt')
    print(f"   ✅ Model loaded: {model}")
    
    print("\n3️⃣ Creating test frame...")
    # Create a dummy frame
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    print(f"   ✅ Frame created: {frame.shape}")
    
    print("\n4️⃣ Running inference...")
    results = model.track(frame, persist=True, verbose=False)
    print(f"   ✅ Inference successful")
    print(f"   Results: {len(results)} result(s)")
    
    if results:
        print(f"   First result: {results[0]}")
        print(f"   Boxes: {results[0].boxes if results[0].boxes else 'None'}")
        print(f"   Keypoints: {results[0].keypoints if results[0].keypoints else 'None'}")
    
    print("\n✅ YOLO is working correctly!")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
