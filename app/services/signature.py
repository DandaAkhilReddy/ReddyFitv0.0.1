from __future__ import annotations

import hashlib

from app.schemas.scan import VisionJSON


def composition_hash(v: VisionJSON, adonis_index: float, symmetry_score: int) -> str:
    s = f"{v.body_fat_percent:.1f}|{v.chest_circumference_cm:.1f}|{v.waist_circumference_cm:.1f}|{v.hip_circumference_cm:.1f}|{adonis_index:.2f}|{symmetry_score:.1f}"
    h = hashlib.sha256(s.encode("utf-8")).hexdigest().upper()
    return h[:6]


def body_signature_id(body_type: str, v: VisionJSON, adonis_index: float, symmetry_score: int) -> str:
    hx = composition_hash(v, adonis_index, symmetry_score)
    return f"{body_type}-BF{v.body_fat_percent:.1f}-{hx}-AI{adonis_index:.2f}"

