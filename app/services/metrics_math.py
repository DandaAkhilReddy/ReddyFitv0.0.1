from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.schemas.scan import VisionJSON


BodyType = Literal["VTaper", "Classic", "Rectangular", "Apple", "Pear", "Balanced"]


@dataclass
class ComputedOut:
    adonis_index: float
    symmetry_score: int
    aesthetic_score: int
    body_type: BodyType
    confidence_overall_0_1: float


def adonis_index(shoulder_width_cm: float, waist_cm: float) -> float:
    if waist_cm <= 0:
        return 0.0
    return round(shoulder_width_cm / waist_cm, 4)


def _score_ratio(actual: float, target: float, tolerance: float = 0.15) -> float:
    if target <= 0:
        return 0.0
    dev = abs(actual - target) / target
    return max(0.0, 1.0 - (dev / tolerance))


def symmetry_score(v: VisionJSON, gender: str | None = None) -> int:
    g = (gender or "male").lower()
    whr_target = 0.85 if g == "male" else 0.70
    chest_waist_target = 1.5 if g == "male" else 1.35
    bicep_chest_target = 0.36
    thigh_waist_target = 0.65
    shoulder_hip_target = 1.25 if g == "male" else 1.05

    ratios = []
    ratios.append(_score_ratio(v.waist_circumference_cm / v.hip_circumference_cm, whr_target))
    ratios.append(_score_ratio(v.chest_circumference_cm / v.waist_circumference_cm, chest_waist_target))
    ratios.append(_score_ratio(v.bicep_circumference_cm / v.chest_circumference_cm, bicep_chest_target))
    ratios.append(_score_ratio(v.thigh_circumference_cm / v.waist_circumference_cm, thigh_waist_target))
    ratios.append(_score_ratio(v.shoulder_width_cm / v.hip_circumference_cm, shoulder_hip_target))
    upper_lower_actual = (v.chest_circumference_cm + v.bicep_circumference_cm) / (
        v.thigh_circumference_cm + max(v.calf_circumference_cm, 1e-3)
    )
    ratios.append(_score_ratio(upper_lower_actual, 1.0))
    return int(round((sum(ratios) / len(ratios)) * 100))


def classify_body_type(v: VisionJSON, ai: float) -> BodyType:
    shoulder_waist = v.shoulder_width_cm / v.waist_circumference_cm
    chest_waist = v.chest_circumference_cm / v.waist_circumference_cm
    hip_waist = v.hip_circumference_cm / v.waist_circumference_cm

    if shoulder_waist >= 1.45 and chest_waist >= 1.35 and v.body_fat_percent <= 20:
        return "VTaper"
    if shoulder_waist <= 1.2 and chest_waist <= 1.2:
        return "Rectangular"
    if (v.waist_circumference_cm / v.hip_circumference_cm) >= 0.95 and v.waist_circumference_cm > v.chest_circumference_cm:
        return "Apple"
    if hip_waist >= 1.15 and (v.shoulder_width_cm / v.hip_circumference_cm) <= 1.05:
        return "Pear"
    # Balanced vs Classic
    dev_phi = abs(ai - 1.618) / 1.618
    return "Classic" if dev_phi <= 0.15 else "Balanced"


def aesthetic_score(v: VisionJSON, ai: float, sym: int) -> int:
    # Golden 40%
    dev_phi = abs(ai - 1.618) / 1.618
    golden_sub = max(0.0, 1.0 - (dev_phi / 0.25)) * 40.0

    # Symmetry 30%
    symmetry_sub = (sym / 100.0) * 30.0

    # Composition 20%: peak at 10-15 (male) / 18-25 (female). Use a soft parabola.
    # Without gender, assume male range for now.
    bf = v.body_fat_percent
    ideal_low, ideal_high = 10.0, 15.0
    if bf < ideal_low:
        comp = max(0.0, 1.0 - (ideal_low - bf) / 10.0)
    elif bf > ideal_high:
        comp = max(0.0, 1.0 - (bf - ideal_high) / 20.0)
    else:
        comp = 1.0
    composition_sub = comp * 20.0

    # Posture 10%
    posture_sub = (v.posture_rating_0_10 / 10.0) * 10.0

    total = golden_sub + symmetry_sub + composition_sub + posture_sub
    return int(round(min(100.0, max(0.0, total))))

