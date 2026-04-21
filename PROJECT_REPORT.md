# AI Cheating Detection and Remote Interview Proctoring System

## Project Summary

This repository implements an AI-assisted remote interview proctoring system with multi-modal monitoring. It uses a Flask backend, Socket.IO real-time communication, OpenCV and YOLO vision analysis, audio processing, and React-based candidate and interviewer frontends. The project directory also contains a second implementation track (`backend_v2`, `frontend_v2`), model assets, tests, and documentation notes.

The provided LaTeX report in the workspace is a project-documentation-style analysis of this same codebase, and this markdown report mirrors that narrative in developer-friendly form.

---

## Repository Structure

### Top-level folders
- `backend/` - main Flask-based backend with routes, services, socket handlers, model assets, and tests.
- `backend_v2/` - alternate simplified backend implementation and evidence folder.
- `frontend/` - original frontend workspace containing `candidate-app` and `interviewer-dashboard` React apps.
- `frontend_v2/` - revised frontend track with separate `candidate-app` and `interviewer-dashboard` projects.
- `hf-space-temp/` - temporary Hugging Face space deployment folder.
- `logs/` - runtime logs and artifacts.
- `data/` - data storage and related datasets.
- `overleaf_ready/`, `overleaf_upload/` - report source and upload packages.
- `yolov8n.pt`, `yolov8n-pose.pt` - YOLO model weights used by backend vision analysis.

### Important backend subfolders
- `backend/app/routes/` - REST route handlers for video, audio, session, fusion, dashboard, and AI services.
- `backend/app/services/` - analysis modules for vision, audio, fraud aggregation, report generation, speaker verification, and more.
- `backend/app/socket_handlers/` and `backend/app/socket_handlers.py` - real-time Socket.IO event processors.
- `backend/evidence/` - evidence snapshot storage.

### Important frontend subfolders
- `frontend/candidate-app/` - candidate-side browser app that captures webcam, microphone, and tab events.
- `frontend/interviewer-dashboard/` - interviewer dashboard with live alerting, risk meters, and monitoring controls.
- `frontend_v2/candidate-app/` and `frontend_v2/interviewer-dashboard/` - newer split apps with separate package manifests.

---

## Backend Overview

### Application startup
- `backend/run.py` is the backend entry point.
- It configures PyTorch/YOLO compatibility and launches a Flask app with Socket.IO.
- It uses `eventlet` in cloud-like environments and threading locally.

### Flask app initialization
- `backend/app/__init__.py` creates the Flask app, enables CORS, registers blueprints, initializes SQLAlchemy, configures Socket.IO, serves evidence images, and creates the SQLite database.
- The app exposes a root health endpoint at `/`.

### Configuration
- `backend/app/config.py` defines application settings and thresholds for proctoring, audio analysis, session lifetime, ASR, and AI authenticity detection.
- It includes configuration classes for development, production, and testing.

### Extensions
- `backend/app/extensions.py` defines shared Flask extensions: `SQLAlchemy`, `SocketIO`, and a global PyTorch lock.

### Backend features
- Video frame analysis and face/gaze monitoring.
- Audio stream analysis and authenticity detection.
- Real-time session state tracking.
- Fraud score aggregation and explanation.
- Evidence image serving for suspicious events.
- Session lifecycle routes such as start/finalize.

---

## Backend Components

### Core route modules
- `backend/app/routes/video_routes.py` - video ingestion and analysis endpoints.
- `backend/app/routes/audio_routes.py` - audio upload and analysis endpoints.
- `backend/app/routes/fusion_routes.py` - score aggregation functionality.
- `backend/app/routes/ai_detection_routes.py` - session start, finalization, and detection orchestration.
- `backend/app/routes/dashboard_routes.py` - dashboard-specific endpoints.
- `backend/app/routes/timeline_routes.py` - timeline/history retrieval.
- `backend/app/routes/session_routes.py` - session lifecycle management.
- `backend/app/routes/health_routes.py` - health checks.

### Socket handlers
- `backend/app/socket_handlers.py` defines Socket.IO listeners for events such as `video_frame`.
- It decodes base64 camera frames, invokes face and gaze analysis, calculates averaged video scores, and emits `fraud_alert` messages.

### Analysis services
- Vision and detection modules:
  - `app/services/video_analyzer.py`
  - `app/services/eye_gaze_tracking.py`
  - `app/services/head_pose_estimation.py`
  - `app/services/face_detection.py`
  - `app/services/stable_vision_engine.py`
- Audio and speech modules:
  - `app/services/audio_analysis.py`
  - `app/services/audio_ai.py`
  - `app/services/enhanced_audio_engine.py`
  - `app/services/transcription_service.py`
  - `app/services/whisper_detection.py`
- AI authenticity and language analysis:
  - `app/services/ai_text_detector.py`
  - `app/services/linguistic_analyzer.py`
  - `app/services/speaker_verification.py`
  - `app/services/authenticity_features.py`
- Aggregation and reporting:
  - `app/services/fusion_state.py`
  - `app/services/fraud_aggregator.py`
  - `app/services/final_report_engine.py`

### Data persistence
- The backend uses SQLite by default with `SQLALCHEMY_DATABASE_URI = "sqlite:///cheating.db"`.
- There are evidence snapshots served from `/evidence/<session>/<filename>`.

---

## Frontend Overview

### Candidate application
- `frontend/candidate-app/src/CandidateApp.jsx` is the main candidate UI component.
- It includes:
  - `WebcamSender` for camera frames.
  - `MicrophoneSender` for audio capture.
  - `TabTracker` for browser visibility/tab switch detection.
- Uses a fixed session ID `session_01` in the sample code.
- Communicates with backend APIs and Socket.IO for real-time monitoring.

### Interviewer dashboard
- `frontend/interviewer-dashboard/src/pages/Dashboard.jsx` is the central dashboard page.
- It listens for `fraud_alert` Socket.IO events and displays:
  - live alerts and timestamps,
  - audio score,
  - video score,
  - tab switch violations,
  - session start/end controls,
  - risk meter and alert components.
- Uses a browser-side microphone analyzer to compute an approximate live audio score and tab visibility events to count suspicious focus loss.

### Frontend dependencies
- Candidate and interviewer apps use React 18 in `frontend/`, while `frontend_v2/` uses React 19.
- Shared frontend packages include:
  - `socket.io-client`
  - `axios`
  - `react-scripts`
  - `recharts` / `react-chartjs-2` for charting
  - `react-gauge-chart` for risk visualization

---

## Alternate Version Tracks

### `backend_v2/`
- Contains a simplified backend implementation and `run.py` for a leaner version of the system.
- Likely used as a streamlined or experimental branch for faster visual/audio analysis.

### `frontend_v2/`
- Re-splits candidate and interviewer apps into separate React projects.
- Indicates continued development and a cleaner separation between roles.

### `hf-space-temp/`
- Contains a Hugging Face Space deployment template, suggesting an alternate hosting or demo environment.
- Includes `run.py`, requirements, and model assets.

---

## Dependencies

### Backend dependencies (`backend/requirements.txt`)
- `flask`, `flask-cors`, `flask-socketio`, `flask-sqlalchemy`
- `numpy`, `opencv-python-headless`, `ultralytics`
- `librosa`, `scipy`, `scikit-learn`, `pymongo`
- `python-dotenv`, `soundfile`, `torch`, `torchvision`
- `google-generativeai`, `gunicorn`, `eventlet`

### Optional/audio authenticity dependencies (`backend/requirements_authenticity.txt`)
- `git+https://github.com/openai/whisper.git`
- `ffmpeg-python`, `soundfile`, `librosa`, `numba`
- `transformers`, `torch`, `tokenizers`, `sentencepiece`, `sacremoses`
- `nltk`, `textstat`, `regex`, `tqdm`, `more-itertools`

### Frontend dependencies
- `frontend/candidate-app`: React 18, `socket.io-client`
- `frontend/interviewer-dashboard`: React 18, `axios`, `chart.js`, `react-chartjs-2`, `react-gauge-chart`, `recharts`, `socket.io-client`
- `frontend_v2` apps: React 19, `socket.io-client`, `axios`, `lucide-react`

---

## Runtime and Operation

### Backend startup
1. Activate Python environment.
2. Install `backend/requirements.txt`.
3. Run `python backend/run.py`.
4. The server starts at `http://0.0.0.0:5000` by default.

### Candidate frontend
- Start with `npm install` in `frontend/candidate-app`.
- Run `npm start`.
- Uses port `3002` in the package script.

### Interviewer frontend
- Start with `npm install` in `frontend/interviewer-dashboard`.
- Run `npm start`.

---

## Testing and Validation

The repository includes explicit test scripts in `backend/`:
- `test_imports.py`
- `test_alert_levels.py`
- `test_pipeline.py`
- `test_integration.py`
- `test_real_frame.py`
- `test_yolo.py`
- `test_whisper_gpu.py`
- `test_e2e.py`
- `test_fallback.py`

These tests indicate validation targets such as:
- package import compatibility,
- alert mapping,
- pipeline execution,
- integration of audio/video inputs,
- YOLO and ASR behavior,
- fallback handling for detector failures.

---

## Key Observations

### Strengths
- Multi-modal monitoring architecture with video, audio, and session signals.
- Clear backend modularization into routes, services, and socket handlers.
- Evidence capture design with image serving.
- Real-time dashboard design for interviewer feedback.
- Existing versioned workstreams (`backend_v2`, `frontend_v2`) demonstrating iterative improvement.

### Limitations
- Multiple `V1`/`V2` implementations increase maintenance complexity.
- Heuristic thresholds and placeholder-style detection logic are visible in configuration.
- Candidate session IDs are hardcoded in sample React code.
- Root-level frontend README is empty, reducing onboarding clarity.
- There is no single canonical deployment README for the full stack.

---

## Suggested Next Steps

1. Consolidate the canonical backend and frontend track (choose either `backend/` or `backend_v2/`, and `frontend/` or `frontend_v2/`).
2. Add a top-level `README.md` describing how to start backend and both frontends together.
3. Document Socket.IO event contracts and session lifecycle clearly.
4. Create a small `docker-compose.yml` or shell script for local end-to-end startup.
5. Standardize session IDs and make them dynamic rather than hardcoded.

---

## Important Files

- `backend/run.py`
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/socket_handlers.py`
- `backend/app/routes/video_routes.py`
- `backend/app/routes/audio_routes.py`
- `backend/app/services/fraud_aggregator.py`
- `frontend/candidate-app/src/CandidateApp.jsx`
- `frontend/interviewer-dashboard/src/pages/Dashboard.jsx`
- `frontend/candidate-app/package.json`
- `frontend/interviewer-dashboard/package.json`
- `backend/requirements.txt`
- `backend/requirements_authenticity.txt`

---

## Conclusion

This repository is a robust student-grade implementation of an AI-based remote proctoring system. It is centered around a Flask+Socket.IO backend with multi-modal analysis and React frontends for candidate and interviewer roles. The project is rich in features and documentation artifacts, and with a small consolidation effort it can become easier to deploy and extend.
