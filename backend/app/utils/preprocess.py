import numpy as np

def normalize_audio(audio):
    audio = audio.astype(float)
    return audio / (np.max(np.abs(audio)) + 1e-9)
