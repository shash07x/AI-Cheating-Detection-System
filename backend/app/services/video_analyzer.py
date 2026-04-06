import cv2
import numpy as np

def analyze_face(frame: np.ndarray) -> int:
    """
    Analyze face presence in a video frame.
    Returns a score between 0–100.
    """

    if frame is None:
        return 0

    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # OpenCV Haar Cascade (lightweight & stable)
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.3,
            minNeighbors=5
        )

        # No face detected → high suspicion
        if len(faces) == 0:
            return 30

        # One face detected → normal
        if len(faces) == 1:
            return 85

        # Multiple faces → very suspicious
        return 95

    except Exception as e:
        print("Video analyzer error:", e)
        return 50
