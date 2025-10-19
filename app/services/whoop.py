from __future__ import annotations

from typing import Optional

from app.schemas.scan import WhoopSummary


def fetch_whoop_summary(uid: str) -> Optional[WhoopSummary]:
    """Stub for WHOOP/Terra integration. Returns None in scaffold.
    Production: fetch last recovery/strain/sleep and map to WhoopSummary.
    """
    return None

