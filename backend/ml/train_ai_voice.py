import os
import librosa
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split

# =========================================================
# CONFIG — MATCHES YOUR ACTUAL DATASET STRUCTURE
# =========================================================

BASE_PATH = "ml/datasets/ASVSpoof2019/LA"

# Use TRAIN set for training
AUDIO_PATH = os.path.join(
    BASE_PATH,
    "ASVspoof2019_LA_train",
    "flac"
)

# CM (Countermeasure) protocol — NOT ASV
PROTOCOL_FILE = os.path.join(
    BASE_PATH,
    "ASVspoof2019_LA_cm_protocols",
    "ASVspoof2019.LA.cm.train.trn.txt"
)

SAMPLE_RATE = 16000
DURATION = 3  # seconds
N_MELS = 128
MAX_LEN = SAMPLE_RATE * DURATION

# =========================================================
# FEATURE EXTRACTION
# =========================================================

def extract_mel(audio):
    audio = audio[:MAX_LEN]
    if len(audio) < MAX_LEN:
        audio = np.pad(audio, (0, MAX_LEN - len(audio)))

    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=SAMPLE_RATE,
        n_mels=N_MELS
    )
    mel = librosa.power_to_db(mel, ref=np.max)
    return mel


# =========================================================
# LOAD DATA
# =========================================================

X, y = [], []

print("📂 Loading protocol file:", PROTOCOL_FILE)
print("📂 Loading audio from:", AUDIO_PATH)

with open(PROTOCOL_FILE, "r") as f:
    lines = f.readlines()

for line in lines:
    parts = line.strip().split()

    # CM protocol format:
    # <speaker_id> <file_id> <env> <attack_id> <bonafide/spoof>
    file_id = parts[1]
    label = parts[-1]  # bonafide | spoof

    audio_file = os.path.join(AUDIO_PATH, f"{file_id}.flac")
    if not os.path.exists(audio_file):
        continue

    audio, _ = librosa.load(audio_file, sr=SAMPLE_RATE)
    mel = extract_mel(audio)

    X.append(mel)
    y.append(0 if label == "bonafide" else 1)

X = np.array(X)[..., np.newaxis]
y = np.array(y)

print("✅ Dataset loaded")
print("   X shape:", X.shape)
print("   y shape:", y.shape)

# =========================================================
# TRAIN / VALIDATION SPLIT
# =========================================================

X_train, X_val, y_train, y_val = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# =========================================================
# MODEL
# =========================================================

model = tf.keras.Sequential([
    tf.keras.layers.Conv2D(
        32, (3, 3),
        activation="relu",
        input_shape=X_train.shape[1:]
    ),
    tf.keras.layers.MaxPooling2D((2, 2)),

    tf.keras.layers.Conv2D(64, (3, 3), activation="relu"),
    tf.keras.layers.MaxPooling2D((2, 2)),

    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(128, activation="relu"),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.Dense(1, activation="sigmoid")
])

model.compile(
    optimizer="adam",
    loss="binary_crossentropy",
    metrics=["accuracy"]
)

model.summary()

# =========================================================
# TRAIN
# =========================================================

model.fit(
    X_train,
    y_train,
    validation_data=(X_val, y_val),
    epochs=10,
    batch_size=16
)

# =========================================================
# SAVE MODEL
# =========================================================
OUTPUT_PATH = "app/services/ai_voice_model.keras"
model.save(
    "app/services/ai_voice_model.h5",
    save_format="h5"
)
print("✅ Model saved to app/services/ai_voice_model.h5")

