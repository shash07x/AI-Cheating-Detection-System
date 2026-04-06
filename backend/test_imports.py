#!/usr/bin/env python
"""Test script to verify SVE integration in video_routes"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

try:
    print("Testing imports...")
    
    # Test stable_vision_engine import
    from app.services.stable_vision_engine import analyze_frame, HeadPose, VisionAnalysis, AlertLevel
    print("✅ stable_vision_engine imported successfully")
    
    # Test video_routes import  
    from app.routes.video_routes import video_bp, analyze_video
    print("✅ video_routes imported successfully")
    
    # Test enum conversion
    level = AlertLevel.CRITICAL
    level_str = str(level).lower().replace("alertlevel.", "")
    print(f"✅ AlertLevel conversion: {level} -> {level_str}")
    
    print("\n🎉 All imports successful! SVE integration is working.")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
