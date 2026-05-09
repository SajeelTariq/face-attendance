"""
IPCV Face Recognition Engine
Pipeline:
  1. Face Detection  — Haar Cascade (frontalface_default)
  2. Preprocessing   — Grayscale + resize to 100x100
  3. Feature Extract — LBPH (Local Binary Pattern Histogram)
  4. Recognition     — Chi-squared distance matching
"""
import cv2
import numpy as np
from pathlib import Path

FACE_DATA_DIR = Path("face_data")
MODEL_PATH = FACE_DATA_DIR / "lbph_model.yml"
IMAGES_DIR = FACE_DATA_DIR / "images"

FACE_DATA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

CONFIDENCE_THRESHOLD = 85.0  # lower = stricter (chi-squared distance)
FACE_SIZE = (100, 100)


def _to_gray(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def detect_face(image: np.ndarray) -> tuple[np.ndarray | None, tuple]:
    """
    Detect the largest face in an image.
    Returns (face_roi_gray_100x100, (x, y, w, h)) or (None, ()).
    """
    gray = _to_gray(image)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60),
    )
    if len(faces) == 0:
        return None, ()

    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_roi = gray[y : y + h, x : x + w]
    face_roi = cv2.resize(face_roi, FACE_SIZE)
    return face_roi, (x, y, w, h)


def save_face_sample(image: np.ndarray, label: int, sample_id: int) -> bool:
    """Crop and save a face sample for a student (label = student face_label)."""
    face, _ = detect_face(image)
    if face is None:
        return False
    label_dir = IMAGES_DIR / str(label)
    label_dir.mkdir(exist_ok=True)
    out_path = label_dir / f"{sample_id}.jpg"
    cv2.imwrite(str(out_path), face)
    return True


def count_samples(label: int) -> int:
    label_dir = IMAGES_DIR / str(label)
    if not label_dir.exists():
        return 0
    return len(list(label_dir.glob("*.jpg")))


def train_model() -> bool:
    """
    Train the LBPH recognizer on all stored face samples.
    Returns True if training succeeded.
    """
    faces, labels = [], []
    for label_dir in IMAGES_DIR.iterdir():
        if not label_dir.is_dir():
            continue
        label = int(label_dir.name)
        for img_path in label_dir.glob("*.jpg"):
            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                faces.append(img)
                labels.append(label)

    if len(faces) == 0:
        return False

    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=1, neighbors=8, grid_x=8, grid_y=8
    )
    recognizer.train(faces, np.array(labels))
    recognizer.save(str(MODEL_PATH))
    return True


def recognize_face(image: np.ndarray) -> tuple[int | None, float | None]:
    """
    Detect and recognize a face.
    Returns (face_label, confidence) or (None, None) if no match / no model.
    Confidence is chi-squared distance — lower is more confident.
    """
    if not MODEL_PATH.exists():
        return None, None

    face, bbox = detect_face(image)
    if face is None:
        return None, None

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(str(MODEL_PATH))

    label, confidence = recognizer.predict(face)
    if confidence < CONFIDENCE_THRESHOLD:
        return label, round(confidence, 2)
    return None, round(confidence, 2)


def draw_result(image: np.ndarray, bbox: tuple, name: str, confidence: float) -> np.ndarray:
    """Draw bounding box and label on image for display."""
    if not bbox:
        return image
    x, y, w, h = bbox
    color = (0, 200, 0) if name != "Unknown" else (0, 0, 200)
    cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
    label_text = f"{name} ({confidence:.1f})"
    cv2.putText(image, label_text, (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return image
