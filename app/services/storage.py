from __future__ import annotations

import json
import os
from datetime import datetime
from datetime import datetime as dt
from pathlib import Path
from typing import Any, Dict

from app.config import settings


def _ensure_local_dirs():
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Path(Path(settings.data_dir) / "images").mkdir(parents=True, exist_ok=True)
    Path(Path(settings.data_dir) / "scans").mkdir(parents=True, exist_ok=True)


def save_image_local(scan_id: str, angle: str, content: bytes) -> str:
    _ensure_local_dirs()
    img_dir = Path(settings.data_dir) / "images" / scan_id
    img_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{angle}.jpg"
    fpath = img_dir / fname
    with open(fpath, "wb") as f:
        f.write(content)
    return str(fpath)


def _json_default(o):
    if isinstance(o, dt):
        return o.isoformat()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def save_scan_local(scan_id: str, obj: Dict[str, Any]) -> str:
    _ensure_local_dirs()
    outf = Path(settings.data_dir) / "scans" / f"{scan_id}.json"
    obj_copy = {**obj, "savedAt": datetime.utcnow().isoformat()}
    with open(outf, "w", encoding="utf-8") as f:
        json.dump(obj_copy, f, ensure_ascii=False, separators=(",", ":"), default=_json_default)
    return str(outf)


def load_scan_local(scan_id: str) -> Dict[str, Any] | None:
    outf = Path(settings.data_dir) / "scans" / f"{scan_id}.json"
    if not outf.exists():
        return None
    with open(outf, "r", encoding="utf-8") as f:
        return json.load(f)
