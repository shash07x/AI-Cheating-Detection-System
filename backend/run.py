import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
import logging

# Fix Windows console encoding (prevents UnicodeEncodeError with emojis)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# ============================================
# FIX: PyTorch 2.6+ YOLO Compatibility
# MUST BE BEFORE ANY OTHER IMPORTS
# ============================================
import torch
torch.set_num_threads(1)

print("Registering YOLO models as safe globals...")

try:
    safe_classes = []
    try:
        from ultralytics.nn.tasks import DetectionModel
        safe_classes.append(DetectionModel)
    except ImportError:
        pass
    try:
        from ultralytics.nn.tasks import PoseModel
        safe_classes.append(PoseModel)
    except ImportError:
        pass
    try:
        from ultralytics.nn.tasks import SegmentationModel
        safe_classes.append(SegmentationModel)
    except ImportError:
        pass
    try:
        from ultralytics.nn.tasks import ClassificationModel
        safe_classes.append(ClassificationModel)
    except ImportError:
        pass
    
    if safe_classes:
        torch.serialization.add_safe_globals(safe_classes)
        print(f"✅ YOLO models registered successfully ({len(safe_classes)} classes)")
    else:
        print("⚠️ No YOLO model classes found to register")
    
except ImportError as e:
    print(f"⚠️ Could not import ultralytics: {e}")
except Exception as e:
    print(f"⚠️ YOLO registration warning: {e}")

# ============================================
# Setup logging
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# ============================================
# Import Flask app
# ============================================
from app import create_app
from app.extensions import socketio

if __name__ == '__main__':
    logger.info("🚀 Starting AI Proctoring System...")
    
    flask_app = create_app()
    
    logger.info("✅ Flask app created successfully")
    logger.info("📡 Starting SocketIO server on http://127.0.0.1:5000")
    
    socketio.run(
        flask_app,
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )