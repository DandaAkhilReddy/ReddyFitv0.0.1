Body Scan Analysis API (FastAPI Scaffold)

Endpoints
- POST `/scans/` → init scan. Body: `{ "uid": "user-123", "height_cm": 180, "gender": "male", "whoop_linked": false }`
- POST `/scans/{scanId}/images` → upload 3 images. Multipart form fields: `front`, `side`, `back`.
- POST `/scans/{scanId}/finalize` → compute math and persist with provided vision JSON (scaffold). Body includes `uid`, `vision{...}`.
- GET `/scans/{scanId}` → fetch saved result.

Run locally
- Install deps: `pip install -r requirements.txt`
- Start API: `uvicorn app.main:app --reload`

Notes
- Image quality validation, preprocessing, and math analysis are implemented.
- Vision uses Anthropic Claude via Messages API. Set `ANTHROPIC_API_KEY` or use `?mock=true` on analyze.
- WHOOP integration is stubbed (no network calls in scaffold).
- Images and results persist to local `.data/` directory.
 - Angle detection: basic heuristic (face + silhouette width). Enforcement is off by default. Enable by setting `angle_enforcement=True` in settings or env.

Environment
- `ANTHROPIC_API_KEY` for Claude vision
- Optional: `ENVIRONMENT`, `DATA_DIR` (via `.env`)
- Optional thresholds: `image_quality_min_score`, `sharpness_threshold`, `preprocess_max_dim`, `jpeg_quality`, `confidence_threshold`, `angle_enforcement`
 
Azure setup (optional)
- Storage: set `storage_provider=azure`, `azure_storage_connection_string`, `azure_storage_container`, optional `azure_sas_expiry_minutes` (default 60).
- Cosmos DB: set `cosmos_enabled=true`, `cosmos_endpoint`, `cosmos_key`, `cosmos_db`, and container names `cosmos_scans_container` (default `scans`), `cosmos_users_container` (default `users`).
  - The code upserts items keyed by `id=scanId` and `id=uid`.
  - Note: For partitioning, configure containers with `partitionKey` on `/id` or adjust code.
  - On startup, the API will attempt to auto-create the database/containers if missing (best-effort; no error if SDK unavailable).

Project structure
- `app/main.py` – FastAPI app factory and lifespan hooks
- `app/config.py` – centralized settings and thresholds (env-driven)
- `app/version.py` – version string
- `app/core/logging.py` – logging configuration
- `app/routers/` – API routes (`scans.py`)
- `app/schemas/` – Pydantic models for I/O
- `app/services/` – image pipeline, vision, math, storage, signature, whoop
- `pyproject.toml` – formatting/linting config (black, isort, ruff)

Formatting & linting (optional)
- Format: `python -m black .` and `python -m isort .`
- Lint: `python -m ruff check .`

Cloud options (optional)
- Set `storage_provider=gcs`, `gcp_project_id`, and `gcs_bucket_name` to enable GCS (requires google-cloud-storage).
- Set `firestore_enabled=true` and `gcp_project_id` to enable Firestore (requires google-cloud-firestore).
- Default remains local storage/persistence; tests run without cloud SDKs.

Project structure (detailed)
- app/core/errors.py – AppError class and JSON error handler
- app/services/persistence.py – local vs Firestore save/load abstraction
- app/services/storage_cloud.py – optional upload and signed URL generation (GCS stub)
- app/services/pose.py – optional MediaPipe pose estimation helper
