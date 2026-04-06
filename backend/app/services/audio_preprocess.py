import librosa
import numpy as np

SAMPLE_RATE = 16000
MAX_LEN = SAMPLE_RATE * 3  # 3 seconds
N_MELS = 128

def preprocess_audio(audio_np: np.ndarray):
    """
    Converts raw audio numpy array into Mel-spectrogram
    suitable for AI voice detection model
    """

    # Trim / pad audio
    audio_np = audio_np[:MAX_LEN]
    if len(audio_np) < MAX_LEN:
        audio_np = np.pad(audio_np, (0, MAX_LEN - len(audio_np)))

    # Mel Spectrogram
    mel = librosa.feature.melspectrogram(
        y=audio_np,
        sr=SAMPLE_RATE,
        n_mels=N_MELS
    )

    mel_db = librosa.power_to_db(mel, ref=np.max)

    # Shape: (1, height, width, 1)
    return mel_db[np.newaxis, ..., np.newaxis]
