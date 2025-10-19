from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi import Body, Query

from app.schemas.scan import (
    AnalysisComputed,
    ScanInitRequest,
    ScanInitResponse,
    ScanResult,
    ScanStatus,
    VisionJSON,
)
from app.services.image_pipeline import validate_quality, preprocess_image, detect_angle, contour_width
from app.services.metrics_math import adonis_index, symmetry_score, aesthetic_score, classify_body_type
from app.services.storage import save_image_local
from app.services.persistence import save_scan, load_scan
from app.services.whoop import fetch_whoop_summary
from app.services.signature import body_signature_id
from app.services.storage_cloud import upload_image_and_get_url
from app.services.ai_vision import call_claude_with_retry
from pathlib import Path


router = APIRouter()


@router.post("/", response_model=ScanInitResponse)
def create_scan(req: ScanInitRequest) -> ScanInitResponse:
    if not req.uid:
        raise HTTPException(status_code=400, detail="Missing uid")
    scan_id = str(uuid.uuid4())
    return ScanInitResponse(scanId=scan_id, status="in_progress", createdAt=datetime.utcnow())


@router.post("/{scanId}/images")
async def upload_images(
    scanId: str,
    front: UploadFile = File(...),
    side: UploadFile = File(...),
    back: UploadFile = File(...),
):
    try:
        img_front = await front.read()
        img_side = await side.read()
        img_back = await back.read()
    finally:
        await front.close(); await side.close(); await back.close()

    # Validate quality and preprocess
    from app.config import settings
    detected: dict[str, str] = {}
    for name, content in (("front", img_front), ("side", img_side), ("back", img_back)):
        q = validate_quality(content)
        if q.score_0_100 < settings.image_quality_min_score:
            raise HTTPException(status_code=422, detail=f"{name} image quality too low. Please re-upload a clearer photo.")
        processed = preprocess_image(content)
        save_image_local(scanId, name, processed)
        # Angle detection (best-effort)
        ang = detect_angle(processed)
        detected[name] = ang
    # Optional enforcement
    if settings.angle_enforcement:
        have_front = any(v == "front" for v in detected.values())
        have_side = any(v == "side" for v in detected.values())
        if not (have_front and have_side):
            raise HTTPException(status_code=422, detail="Please upload distinct front and side photos (back optional).")
    return {"scanId": scanId, "message": "images uploaded", "detectedAngles": detected}


@router.post("/{scanId}/analyze", response_model=ScanResult)
def analyze_scan(
    scanId: str,
    uid: str = Body(..., embed=True),
    height_cm: Optional[float] = Body(None, embed=True),
    gender: Optional[str] = Body(None, embed=True),
    mock: bool = Query(False, description="Use mock vision output if OpenAI key is absent"),
):
    # Load preprocessed images from local storage
    img_dir = Path(f".data/images/{scanId}")
    paths = {"front": img_dir / "front.jpg", "side": img_dir / "side.jpg", "back": img_dir / "back.jpg"}
    if not all(p.exists() for p in paths.values()):
        raise HTTPException(status_code=400, detail="Images not found. Upload images before analyzing.")

    images = []
    for angle, p in paths.items():
        with open(p, "rb") as f:
            images.append((angle, f.read()))

    # Call vision model (or mock)
    try:
        vision = call_claude_with_retry(images, scan_id=scanId, allow_mock=mock)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vision analysis failed: {e}")

    # Confidence base on model
    completeness = 1.0
    confidence = max(0.0, min(1.0, float(vision.model_confidence_0_1) * completeness))

    # Cross-view consistency: front vs side width heuristic
    front_w = contour_width(open(paths["front"], "rb").read())
    side_w = contour_width(open(paths["side"], "rb").read())
    if front_w and side_w and side_w > 0 and front_w > 0:
        # Expect side narrower than front; if not, penalize
        if side_w >= 0.95 * front_w:
            confidence = max(0.0, confidence - 0.1)

    ai = adonis_index(vision.shoulder_width_cm, vision.waist_circumference_cm)
    sym = symmetry_score(vision, gender)
    aesth = aesthetic_score(vision, ai, sym)
    btype = classify_body_type(vision, ai)
    signature_id = body_signature_id(btype, vision, ai, sym)

    computed = AnalysisComputed(
        adonis_index=ai,
        symmetry_score=sym,
        aesthetic_score=aesth,
        body_type=btype,
        body_signature_id=signature_id,
        confidence_overall_0_1=confidence,
    )

    whoop = fetch_whoop_summary(uid)

    from app.config import settings
    # Resolve URLs (local path or signed URL based on provider)
    image_urls = {k: upload_image_and_get_url(str(v), f"{scanId}/{k}.jpg") for k, v in paths.items()}

    result = ScanResult(
        scanId=scanId,
        uid=uid,
        createdAt=datetime.utcnow(),
        pipeline_version=settings.pipeline_version,
        images=image_urls,
        input={"height_cm": height_cm, "gender": gender},
        vision=vision,
        computed=computed,
        whoop=whoop,
    )

    save_scan(scanId, result.dict())
    return result


@router.post("/{scanId}/finalize", response_model=ScanResult)
def finalize_scan(
    scanId: str,
    uid: str = Body(...),
    vision: VisionJSON = Body(...),
    height_cm: Optional[float] = Body(None),
    gender: Optional[str] = Body(None),
):
    # Compute confidence (simple aggregate placeholder)
    completeness = 1.0
    confidence = max(0.0, min(1.0, float(vision.model_confidence_0_1) * completeness))

    ai = adonis_index(vision.shoulder_width_cm, vision.waist_circumference_cm)
    sym = symmetry_score(vision, gender)
    aesth = aesthetic_score(vision, ai, sym)
    btype = classify_body_type(vision, ai)

    # Minimal signature id (will be set in client/compute layer ideally)
    signature_id = body_signature_id(btype, vision, ai, sym)

    computed = AnalysisComputed(
        adonis_index=ai,
        symmetry_score=sym,
        aesthetic_score=aesth,
        body_type=btype,
        body_signature_id=signature_id,
        confidence_overall_0_1=confidence,
    )

    whoop = fetch_whoop_summary(uid)

    result = ScanResult(
        scanId=scanId,
        uid=uid,
        createdAt=datetime.utcnow(),
        pipeline_version="v0.1",
        images={
            "front": f".data/images/{scanId}/front.jpg",
            "side": f".data/images/{scanId}/side.jpg",
            "back": f".data/images/{scanId}/back.jpg",
        },
        input={"height_cm": height_cm, "gender": gender},
        vision=vision,
        computed=computed,
        whoop=whoop,
    )

    save_scan_local(scanId, result.dict())
    return result


@router.get("/{scanId}", response_model=ScanResult)
def get_scan(scanId: str) -> ScanResult:
    obj = load_scan(scanId)
    if not obj:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResult(**obj)
