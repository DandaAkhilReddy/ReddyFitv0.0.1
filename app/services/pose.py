from __future__ import annotations

"""Optional pose estimation using MediaPipe. Fallback to None if unavailable.
"""

from typing import Optional

try:  # pragma: no cover - optional dependency
    import mediapipe as mp  # type: ignore
except Exception:  # pragma: no cover
    mp = None


def estimate_view(image_rgb) -> Optional[str]:  # noqa: ANN001  (typed loosely to avoid hard dep)
    """Return 'front'|'back'|'side'|None based on landmark geometry.
    Requires mediapipe. If not available, returns None.
    """
    if mp is None:
        return None
    pose = mp.solutions.pose.Pose(static_image_mode=True, enable_segmentation=False)
    res = pose.process(image_rgb)
    if not res.pose_landmarks:
        return None
    # Simple heuristic: visibility of face landmarks vs profile depth
    # This is a placeholder for a richer rule set.
    lms = res.pose_landmarks.landmark
    nose_vis = lms[0].visibility if len(lms) > 0 else 0.0
    left_eye_vis = lms[2].visibility if len(lms) > 2 else 0.0
    right_eye_vis = lms[5].visibility if len(lms) > 5 else 0.0
    visible_eyes = (left_eye_vis > 0.5) + (right_eye_vis > 0.5)
    if nose_vis > 0.5 and visible_eyes == 2:
        return "front"
    if visible_eyes == 0 and nose_vis < 0.3:
        return "back"
    return "side"

