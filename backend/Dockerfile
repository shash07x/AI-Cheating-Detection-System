FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by OpenCV, ffmpeg (for audio), etc.
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (saves ~1.5GB vs GPU version)
# This satisfies torch>=2.0.0 and torchvision>=0.15.0 from requirements.txt
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install remaining dependencies
# Filter out torch/torchvision since we already installed CPU versions above
COPY requirements.txt .
RUN grep -iv "^torch" requirements.txt > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt && \
    rm requirements_filtered.txt

# Copy application code (respects .dockerignore)
COPY . .

# Create directories that the app expects
RUN mkdir -p evidence instance logs

# Expose port 7860 (Hugging Face Spaces default)
EXPOSE 7860

# Start with gunicorn + eventlet for WebSocket support
# Single worker to keep memory usage low
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:7860", "run:flask_app", "--timeout", "120"]
