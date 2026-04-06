"""
Transcription Service - NVIDIA Parakeet TDT (Primary) + Whisper (Fallback)

Pipeline:
  Audio bytes → Parakeet TDT 0.6B (NeMo ASR - in subprocess) → Transcript text
  Fallback: Audio bytes → Whisper (in subprocess) → Transcript text

Both ASR models run in SUBPROCESSES for crash safety.
The main Flask process is never at risk of crashing from model errors.

After transcription, the text goes to Gemini AI for human vs AI detection
(handled separately in ai_text_detector.py).
"""

import os
import sys
import tempfile
import subprocess
import json
import numpy as np
import soundfile as sf
import time
import logging
import threading

logger = logging.getLogger(__name__)

# ================================================
# CONFIG
# ================================================

SAMPLE_RATE = 16000
PARAKEET_AVAILABLE = False
WHISPER_AVAILABLE = False
_checked = False

# ================================================
# 1. CHECK MODEL AVAILABILITY
# ================================================

def _check_models():
    """Check which ASR models are importable (don't load in-process)."""
    global PARAKEET_AVAILABLE, WHISPER_AVAILABLE, _checked
    if _checked:
        return
    _checked = True

    # Check Parakeet (NeMo)
    try:
        import nemo.collections.asr
        PARAKEET_AVAILABLE = True
        logger.info("✅ NVIDIA Parakeet (NeMo ASR) available - will use for transcription")
    except ImportError:
        logger.warning("⚠️ NeMo toolkit not installed - Parakeet unavailable")
        PARAKEET_AVAILABLE = False

    # Check Whisper fallback
    try:
        import whisper
        WHISPER_AVAILABLE = True
        logger.info("✅ OpenAI Whisper available as fallback")
    except ImportError:
        logger.warning("⚠️ openai-whisper not installed")
        WHISPER_AVAILABLE = False


# ================================================
# 2. PARAKEET SUBPROCESS TRANSCRIPTION (PRIMARY)
# ================================================

_PARAKEET_SCRIPT = '''
import sys, json, os, warnings
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
warnings.filterwarnings("ignore")

try:
    import nemo.collections.asr as nemo_asr
    import torch
    
    audio_path = sys.argv[1]
    
    # Load Parakeet TDT 0.6B - NVIDIA's state-of-the-art ASR
    model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v2")
    
    # Use CPU to avoid GPU conflicts with YOLO
    model = model.cpu()
    model.eval()
    
    # Transcribe
    with torch.no_grad():
        transcriptions = model.transcribe([audio_path])
    
    # Handle different NeMo output formats
    if isinstance(transcriptions, list):
        if len(transcriptions) > 0:
            text = transcriptions[0]
            if hasattr(text, 'text'):
                text = text.text
            elif isinstance(text, dict):
                text = text.get('text', str(text))
            else:
                text = str(text)
        else:
            text = ""
    else:
        text = str(transcriptions)
    
    text = text.strip()
    print(json.dumps({"text": text, "model": "parakeet-tdt-0.6b"}))
    
except Exception as e:
    print(json.dumps({"text": "", "error": str(e), "model": "parakeet-error"}))
'''


_WHISPER_SCRIPT = '''
import sys, json, os, warnings
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
warnings.filterwarnings("ignore")

try:
    import whisper
    model = whisper.load_model("tiny", device="cpu")
    result = model.transcribe(sys.argv[1], fp16=False, language="en", task="transcribe")
    text = result.get("text", "").strip()
    print(json.dumps({"text": text, "model": "whisper-tiny"}))
except Exception as e:
    print(json.dumps({"text": "", "error": str(e), "model": "whisper-error"}))
'''


def _run_transcription_subprocess(script_content: str, audio_path: str, 
                                   model_name: str, timeout: int = 60) -> dict:
    """
    Run an ASR model in a separate subprocess.
    If the subprocess crashes, our main process survives.
    """
    try:
        # Write script to temp file
        script_path = os.path.join(tempfile.gettempdir(), f"_asr_{model_name}_worker.py")
        with open(script_path, "w") as f:
            f.write(script_content)
        
        start = time.time()
        logger.info(f"🎤 Running {model_name} in subprocess: {audio_path}")
        
        env = {**os.environ, "KMP_DUPLICATE_LIB_OK": "TRUE"}
        
        result = subprocess.run(
            [sys.executable, script_path, audio_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
        
        elapsed = time.time() - start
        
        if result.returncode != 0:
            stderr_snippet = result.stderr[:300] if result.stderr else "no stderr"
            logger.warning(f"⚠️ {model_name} subprocess failed (exit {result.returncode}): {stderr_snippet}")
            return {}
        
        output = result.stdout.strip()
        if not output:
            logger.warning(f"⚠️ {model_name} subprocess returned empty output")
            return {}
        
        # Parse JSON from last line (avoid NeMo warnings in stdout)
        lines = output.strip().split('\n')
        json_line = None
        for line in reversed(lines):
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                json_line = line
                break
        
        if not json_line:
            logger.warning(f"⚠️ {model_name}: No JSON found in output")
            return {}
        
        data = json.loads(json_line)
        
        if data.get("error"):
            logger.warning(f"⚠️ {model_name} error: {data['error'][:200]}")
            return {}
        
        transcript = data.get("text", "").strip()
        model_used = data.get("model", model_name)
        
        logger.info(f"✅ {model_used} result ({elapsed:.1f}s): '{transcript[:80]}'")
        
        if not transcript:
            return {}
        
        # Get audio duration
        try:
            audio_data, sr = sf.read(audio_path)
            duration = len(audio_data) / sr
        except Exception:
            duration = 0.0
        
        return {
            "text": transcript,
            "speech_duration": round(duration, 2),
            "first_speech_time": 0.0,
            "avg_pause": 0.0,
            "model": model_used,
            "processing_time": round(elapsed, 2)
        }
    
    except subprocess.TimeoutExpired:
        logger.warning(f"⚠️ {model_name} subprocess timed out after {timeout}s")
        return {}
    except Exception as e:
        logger.error(f"❌ {model_name} subprocess error: {e}")
        return {}


# ================================================
# 3. MAIN TRANSCRIPTION FUNCTION
# ================================================

_transcription_lock = threading.Lock()

def transcribe_audio(audio_bytes: bytes) -> dict:
    """
    Main transcription entry point.
    
    Priority:
      1. NVIDIA Parakeet TDT 0.6B (best quality, subprocess)
      2. OpenAI Whisper tiny (fallback, subprocess)
      3. Basic energy detection (no transcription)
    
    Args:
        audio_bytes: Raw PCM int16 audio @ 16kHz
    
    Returns:
        dict with 'text', 'speech_duration', 'model', etc.
    """
    if not audio_bytes or len(audio_bytes) < 1000:
        return {}

    try:
        # Prepare audio
        if len(audio_bytes) % 2 != 0:
            audio_bytes = audio_bytes[:-1]

        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
        if audio_np.size < 500:
            return {}

        audio_float = audio_np.astype(np.float32) / 32768.0

        # Energy check
        rms = float(np.sqrt(np.mean(audio_float ** 2)))
        if rms < 0.001:
            return {}

        # Limit to 30s max
        max_samples = SAMPLE_RATE * 30
        if len(audio_float) > max_samples:
            audio_float = audio_float[:max_samples]

        # Only one transcription at a time
        acquired = _transcription_lock.acquire(timeout=2)
        if not acquired:
            logger.info("Transcription lock busy, skipping")
            return {"text": "[speech detected]", "model": "lock-busy"}

        try:
            # Save to temp wav
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                sf.write(tmp.name, audio_float, SAMPLE_RATE)
                temp_path = tmp.name

            result = {}

            # 1. Try Parakeet (primary)
            if PARAKEET_AVAILABLE:
                result = _run_transcription_subprocess(
                    _PARAKEET_SCRIPT, temp_path, "parakeet", timeout=60
                )
                if result and result.get("text") and result["text"] not in ("[speech detected]", ""):
                    logger.info(f"🎯 Parakeet transcription: '{result['text'][:80]}'")
                    _cleanup_temp(temp_path)
                    return result

            # 2. Try Whisper (fallback)
            if WHISPER_AVAILABLE:
                result = _run_transcription_subprocess(
                    _WHISPER_SCRIPT, temp_path, "whisper", timeout=30
                )
                if result and result.get("text") and result["text"] not in ("[speech detected]", ""):
                    logger.info(f"🎯 Whisper transcription: '{result['text'][:80]}'")
                    _cleanup_temp(temp_path)
                    return result

            # 3. Basic fallback
            _cleanup_temp(temp_path)
            duration = len(audio_float) / 16000.0
            return {
                "text": "[speech detected]",
                "speech_duration": round(duration, 2),
                "first_speech_time": 0.0,
                "avg_pause": 0.0,
                "model": "basic-energy",
                "processing_time": 0.0
            }

        finally:
            _transcription_lock.release()

    except Exception as e:
        logger.error(f"❌ Transcription pipeline error: {e}")
        return {}


def _cleanup_temp(path):
    """Safely remove temp file."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ================================================
# 4. INITIALIZATION
# ================================================

def initialize_transcription():
    """Initialize transcription availability at startup."""
    logger.info("🔧 Initializing transcription service...")
    _check_models()
    
    if PARAKEET_AVAILABLE:
        logger.info("✅ Transcription: NVIDIA Parakeet TDT 0.6B (primary, subprocess)")
    if WHISPER_AVAILABLE:
        logger.info("✅ Transcription: OpenAI Whisper (fallback, subprocess)")
    if not PARAKEET_AVAILABLE and not WHISPER_AVAILABLE:
        logger.warning("⚠️ Transcription: Basic energy detection only")
    
    logger.info("🔍 AI Detection: Google Gemini (for human vs AI text classification)")


# Auto-initialize on import
initialize_transcription()
