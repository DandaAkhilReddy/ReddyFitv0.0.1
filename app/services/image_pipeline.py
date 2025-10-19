from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Literal, Tuple, Optional

import numpy as np

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover - optional in this scaffold
    Image = None
    ImageOps = None

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - optional in this scaffold
    cv2 = None


Angle = Literal["front", "side", "back", "unknown"]


@dataclass
class ImageQuality:
    width: int
    height: int
    sharpness: float
    size_bytes: int
    score_0_100: float
    rotated: bool


def _laplacian_variance(img: np.ndarray) -> float:
    if cv2 is None:
        return 60.0  # optimistic default if cv2 unavailable
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _read_image_bytes(data: bytes) -> Tuple[np.ndarray, bool, Tuple[int, int]]:
    rotated = False
    if Image is None:
        # Fallback: try decoding with cv2
        if cv2 is None:
            raise RuntimeError("No imaging backend available")
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        h, w = img.shape[:2]
        return img, rotated, (w, h)
    img = Image.open(io.BytesIO(data))
    w, h = img.size
    if ImageOps is not None:
        img2 = ImageOps.exif_transpose(img)
        rotated = img2 is not img
        img = img2
        w, h = img.size
    # Convert to BGR np array for cv2 ops
    arr = np.array(img.convert("RGB"))[:, :, ::-1]
    return arr, rotated, (w, h)


def validate_quality(data: bytes) -> ImageQuality:
    img, rotated, (w, h) = _read_image_bytes(data)
    size_bytes = len(data)
    # Resolution constraints (from settings)
    from app.config import settings
    res_ok = (
        (w >= settings.image_min_width and h >= settings.image_min_height)
        and (w <= settings.image_max_width and h <= settings.image_max_height)
    )
    # Sharpness
    sharpness = _laplacian_variance(img)
    # Composite score (simple heuristic)
    score = 0.0
    score += 40 if res_ok else 0
    score += 40 if sharpness >= settings.sharpness_threshold else (sharpness / max(settings.sharpness_threshold, 1e-3)) * 40
    # Size window
    score += 20 if (settings.image_min_size_bytes <= size_bytes <= settings.image_max_size_bytes) else 10
    return ImageQuality(width=w, height=h, sharpness=sharpness, size_bytes=size_bytes, score_0_100=score, rotated=rotated)


def preprocess_image(data: bytes, max_dim: int | None = None, jpeg_quality: int | None = None) -> bytes:
    img, _rot, (w, h) = _read_image_bytes(data)
    if cv2 is None:
        return data  # fallback
    from app.config import settings
    if max_dim is None:
        max_dim = settings.preprocess_max_dim
    if jpeg_quality is None:
        jpeg_quality = settings.jpeg_quality
    # Resize preserving aspect
    scale = min(1.0, max_dim / max(w, h))
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    # Brightness/contrast normalization using CLAHE in LAB
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    norm = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    # JPEG compress
    ok, enc = cv2.imencode(".jpg", norm, [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)])
    if not ok:
        raise RuntimeError("Failed to encode image")
    return bytes(enc)


def detect_angle(data: bytes) -> Angle:
    """Heuristic angle classification using MediaPipe (if available),
    then fallback to face detection and silhouette width.

    - If a face is detected: front
    - Else if person width is very narrow relative to height: side
    - Else: unknown (could be back or ambiguous)
    """
    try:
        if cv2 is None:
            return "unknown"
        img, _rot, (w, h) = _read_image_bytes(data)
        # Try MediaPipe (if installed)
        try:
            from app.services.pose import estimate_view  # lazy import
            view = estimate_view(img[:, :, ::-1])  # convert BGR->RGB
            if view:
                return view  # type: ignore[return-value]
        except Exception:
            pass
        # Face detection (frontal)
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
            if len(faces) > 0:
                return "front"
        except Exception:
            pass

        # Silhouette width heuristic
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        # Otsu threshold to get foreground roughly
        _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Ensure person is white: invert if needed (assume person darker than background typically)
        if np.mean(thr) > 127:
            thr = 255 - thr
        cnts, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return "unknown"
        cnt = max(cnts, key=cv2.contourArea)
        x, y, ww, hh = cv2.boundingRect(cnt)
        ratio = ww / max(hh, 1)
        if ratio <= 0.35:
            return "side"
        return "unknown"
    except Exception:
        return "unknown"


def contour_width(data: bytes) -> Optional[int]:
    """Return the width of the largest foreground contour bounding box (pixels), or None."""
    if cv2 is None:
        return None
    try:
        img, _rot, (w, h) = _read_image_bytes(data)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if np.mean(thr) > 127:
            thr = 255 - thr
        cnts, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None
        cnt = max(cnts, key=cv2.contourArea)
        x, y, ww, hh = cv2.boundingRect(cnt)
        return int(ww)
    except Exception:
        return None
