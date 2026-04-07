import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import torch
torch.set_num_threads(1)
import logging

logger = logging.getLogger(__name__)

# Global model cache
_yolo_models = {}
_yolo_available = False

# Try to import YOLO, handle import errors
try:
    from ultralytics import YOLO
    _yolo_available = True
    logger.info("✅ YOLO import successful")
except Exception as e:
    logger.warning(f"⚠️ YOLO import failed: {e}")
    logger.warning("   Fallback face detection will be used")
    _yolo_available = False


def load_yolo_safe(model_name='yolov8n.pt'):
    global _yolo_models
    
    if not _yolo_available:
        logger.warning(f"YOLO not available, returning None for {model_name}")
        return None
    
    if model_name in _yolo_models:
        return _yolo_models[model_name]
    
    try:
        # Register YOLO classes as safe globals for PyTorch 2.6+
        from ultralytics.nn.tasks import DetectionModel, PoseModel, SegmentationModel
        
        torch.serialization.add_safe_globals([
            DetectionModel,
            PoseModel,
            SegmentationModel
        ])
        
        logger.info(f"Loading {model_name}...")
        
        # Load model
        model = YOLO(model_name)
        
        # Cache it
        _yolo_models[model_name] = model
        
        logger.info(f"OK: {model_name} loaded successfully")
        
        return model
    
    except Exception as e:
        logger.error(f"Failed to load {model_name}: {e}")
        return None