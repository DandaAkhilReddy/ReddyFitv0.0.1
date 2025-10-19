from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app


def make_jpeg_bytes(w=800, h=1200, color=(200, 200, 200)) -> bytes:
    img = Image.new("RGB", (w, h), color)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_full_flow_with_mock():
    client = TestClient(app)

    # Init
    r = client.post("/scans/", json={"uid": "test-user"})
    assert r.status_code == 200, r.text
    scan_id = r.json()["scanId"]

    # Upload images
    files = {
        "front": ("front.jpg", make_jpeg_bytes(), "image/jpeg"),
        "side": ("side.jpg", make_jpeg_bytes(), "image/jpeg"),
        "back": ("back.jpg", make_jpeg_bytes(), "image/jpeg"),
    }
    r = client.post(f"/scans/{scan_id}/images", files=files)
    assert r.status_code == 200, r.text

    # Analyze with mock
    r = client.post(
        f"/scans/{scan_id}/analyze?mock=true",
        json={"uid": "test-user", "height_cm": 180, "gender": "male"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["scanId"] == scan_id
    assert data["computed"]["body_signature_id"].startswith(data["computed"]["body_type"])  # sanity

    # Fetch
    r = client.get(f"/scans/{scan_id}")
    assert r.status_code == 200
    got = r.json()
    assert got["scanId"] == scan_id

