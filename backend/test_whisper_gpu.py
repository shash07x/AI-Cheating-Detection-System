"""Test Whisper small on GPU"""
import whisper, torch, time, numpy as np

print("CUDA:", torch.cuda.is_available())
print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None")

print("Loading Whisper 'small' on GPU...")
start = time.time()
model = whisper.load_model("small", device="cuda")
print(f"Model loaded in {time.time()-start:.1f}s!")

# Test with silence/noise (just for speed test)
audio = np.random.randn(16000 * 4).astype(np.float32) * 0.01
start = time.time()
result = model.transcribe(audio, fp16=True, language="en")
elapsed = time.time() - start
print(f"Transcription speed: {elapsed:.1f}s for 4s audio on GPU")
print(f"Text: '{result['text'][:100]}'")
print("SUCCESS!")
