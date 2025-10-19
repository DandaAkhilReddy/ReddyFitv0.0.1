from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, conint, confloat


BodyType = Literal["VTaper", "Classic", "Rectangular", "Apple", "Pear", "Balanced"]


class ScanInitRequest(BaseModel):
    uid: str
    height_cm: Optional[confloat(gt=80, lt=250)] = None
    gender: Optional[Literal["male", "female", "other"]] = None
    goal: Optional[str] = None
    whoop_linked: bool = False


class ScanInitResponse(BaseModel):
    scanId: str
    status: Literal["in_progress", "created"] = "in_progress"
    createdAt: datetime


class VisionJSON(BaseModel):
    chest_circumference_cm: confloat(gt=30, lt=250)
    waist_circumference_cm: confloat(gt=30, lt=250)
    hip_circumference_cm: confloat(gt=30, lt=250)
    shoulder_width_cm: confloat(gt=20, lt=120)
    bicep_circumference_cm: confloat(gt=10, lt=80)
    thigh_circumference_cm: confloat(gt=20, lt=120)
    calf_circumference_cm: confloat(gt=15, lt=80)
    body_fat_percent: confloat(gt=3, lt=60)
    posture_rating_0_10: confloat(ge=0, le=10)
    model_confidence_0_1: confloat(ge=0, le=1)
    body_type_guess: Optional[str] = None


class AnalysisComputed(BaseModel):
    adonis_index: confloat(gt=0, lt=4)
    symmetry_score: conint(ge=0, le=100)
    aesthetic_score: conint(ge=0, le=100)
    body_type: BodyType
    body_signature_id: str
    confidence_overall_0_1: confloat(ge=0, le=1)


class WhoopSummary(BaseModel):
    recovery_score: Optional[confloat(ge=0, le=100)] = None
    strain_score: Optional[confloat(ge=0, le=21)] = None
    sleep_hours: Optional[confloat(ge=0, le=24)] = None


class ScanResult(BaseModel):
    scanId: str
    uid: str
    createdAt: datetime
    pipeline_version: str
    images: dict
    input: dict
    vision: VisionJSON
    computed: AnalysisComputed
    whoop: Optional[WhoopSummary] = None


class ScanStatus(BaseModel):
    scanId: str
    status: Literal["in_progress", "completed", "failed"]
    message: Optional[str] = None
