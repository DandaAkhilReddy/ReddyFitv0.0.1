from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app


def make_jpeg_bytes(w=800, h=1200, color=(180, 180, 180)) -> bytes:
    img = Image.new("RGB", (w, h), color)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def main():
    client = TestClient(app)

    r = client.post("/scans/", json={"uid": "smoke-user"})
    r.raise_for_status()
    scan_id = r.json()["scanId"]

    files = {
        "front": ("front.jpg", make_jpeg_bytes(), "image/jpeg"),
        "side": ("side.jpg", make_jpeg_bytes(), "image/jpeg"),
        "back": ("back.jpg", make_jpeg_bytes(), "image/jpeg"),
    }
    r = client.post(f"/scans/{scan_id}/images", files=files)
    r.raise_for_status()

    r = client.post(
        f"/scans/{scan_id}/analyze",
        json={"uid": "smoke-user", "height_cm": 180, "gender": "male"},
    )
    print("Status:", r.status_code)
    print("Body:", r.text[:500])
    r.raise_for_status()
    print("Smoke test success. ScanId:", scan_id)


if __name__ == "__main__":
    main()

