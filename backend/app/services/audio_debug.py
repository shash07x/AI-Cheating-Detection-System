import uuid
from pathlib import Path

AUDIO_DIR = Path("logs/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def save_audio_chunk(chunk: bytes):
    filename = AUDIO_DIR / f"{uuid.uuid4()}.webm"
    with open(filename, "wb") as f:
        f.write(chunk)
