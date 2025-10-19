from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Tuple, Optional

from pydantic import ValidationError

from app.config import settings
from app.schemas.scan import VisionJSON


def build_prompt() -> Tuple[str, str]:
    system = (
        "You are an expert physique analyst. Return only a valid JSON object with the exact keys "
        "and numeric values. Units: centimeters for lengths, percent for body fat. No code fences or extra text."
    )
    user = (
        "Analyze the person’s physique from three images (front, side, back). Use all views. "
        "Output JSON with keys: chest_circumference_cm, waist_circumference_cm, hip_circumference_cm, "
        "shoulder_width_cm, bicep_circumference_cm, thigh_circumference_cm, calf_circumference_cm, "
        "body_fat_percent, posture_rating_0_10, model_confidence_0_1, body_type_guess. "
        "Use cm and percent only."
    )
    return system, user


def _extract_json(raw: str) -> Dict[str, Any]:
    # Strategy 1: direct parse
    try:
        return json.loads(raw)
    except Exception:
        pass
    # Strategy 2: strip code fences
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(json|\w+)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # Strategy 3: regex to find outermost JSON object
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        snippet = m.group(0)
        # Remove trailing commas (simple cleanup)
        snippet = re.sub(r",\s*([}\]])", r"\1", snippet)
        # Remove percent symbols
        snippet = snippet.replace("%", "")
        try:
            return json.loads(snippet)
        except Exception:
            pass
    # Strategy 4: tolerant fixups
    snippet = cleaned.replace("%", "")
    snippet = re.sub(r",\s*([}\]])", r"\1", snippet)
    return json.loads(snippet)


def coerce_and_validate(obj: Dict[str, Any]) -> VisionJSON:
    def num(x):
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            x2 = re.sub(r"[^0-9.]+", "", x)
            return float(x2) if x2 else 0.0
        return float(x)

    # Range-based inches detection for large circ. fields
    def maybe_inches_to_cm(v: float) -> float:
        # If value likely in inches (typical human circ in inches ~ 20–60)
        if 20 <= v <= 70:
            return v * 2.54
        return v

    keys_in = [
        "chest_circumference_cm",
        "waist_circumference_cm",
        "hip_circumference_cm",
        "shoulder_width_cm",
        "bicep_circumference_cm",
        "thigh_circumference_cm",
        "calf_circumference_cm",
        "body_fat_percent",
        "posture_rating_0_10",
        "model_confidence_0_1",
        "body_type_guess",
    ]

    out: Dict[str, Any] = {}
    major_circ = {"chest_circumference_cm", "waist_circumference_cm", "hip_circumference_cm"}
    for k in keys_in:
        if k not in obj:
            continue
        v = obj[k]
        if k in ("body_type_guess",):
            out[k] = v
        elif k in ("posture_rating_0_10", "model_confidence_0_1", "body_fat_percent"):
            out[k] = num(v)
        else:
            cm = num(v)
            # Heuristic detect inches only for major circumferences
            if k in major_circ and cm < 70:
                cm = maybe_inches_to_cm(cm)
            out[k] = cm

    return VisionJSON(**out)


def call_claude_with_retry(
    images: List[Tuple[str, bytes]],
    scan_id: str,
    allow_mock: bool = False,
) -> VisionJSON:
    """Call Anthropic Claude (vision) with retry and robust JSON extraction.
    If ANTHROPIC_API_KEY is not configured and allow_mock=True, returns a deterministic mock.
    """
    # Mock path for offline/local testing
    if allow_mock:
        mock = {
            "chest_circumference_cm": 105.0,
            "waist_circumference_cm": 82.0,
            "hip_circumference_cm": 98.0,
            "shoulder_width_cm": 50.0,
            "bicep_circumference_cm": 36.0,
            "thigh_circumference_cm": 60.0,
            "calf_circumference_cm": 38.0,
            "body_fat_percent": 15.0,
            "posture_rating_0_10": 8.0,
            "model_confidence_0_1": 0.9,
            "body_type_guess": "VTaper",
        }
        return coerce_and_validate(mock)

    # Real call via Anthropic Messages API
    try:
        from anthropic import Anthropic  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Anthropic SDK not installed. Add 'anthropic' to requirements.") from e

    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured and mock disabled")

    client = Anthropic(api_key=settings.anthropic_api_key)
    system, user = build_prompt()

    import base64

    def img_to_block(data: bytes) -> Dict[str, Any]:
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64.b64encode(data).decode("ascii"),
            },
        }

    user_content: List[Dict[str, Any]] = [{"type": "text", "text": user}]
    for angle, data in images:
        user_content.append(img_to_block(data))

    last_exc: Optional[Exception] = None
    for attempt in range(3):
        try:
            resp = client.messages.create(
                model=settings.anthropic_model_vision,
                max_tokens=700,
                temperature=0.3,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            )
            # Concatenate text blocks
            chunks = [c.text for c in resp.content if getattr(c, "type", None) == "text"]
            text = "\n".join(chunks).strip()
            obj = _extract_json(text)
            return coerce_and_validate(obj)
        except Exception as e:
            last_exc = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Vision analysis failed after retries: {last_exc}")


def extract_vision_json(raw_text: str) -> VisionJSON:
    try:
        obj = _extract_json(raw_text)
        return coerce_and_validate(obj)
    except ValidationError as ve:
        raise RuntimeError(f"Schema validation failed: {ve}")
