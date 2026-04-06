import traceback
try:
    import nemo.collections.asr as nemo_asr
    print("ASR imported OK")
    model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v2")
    print("Model loaded!")
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
