from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.logging import configure_logging
from app.core.errors import app_error_handler, AppError
from app.services.persistence import ensure_persistence_setup
from app.config import settings
from pathlib import Path

from app.routers.scans import router as scans_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure logging and ensure data dir exists
    configure_logging()
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    # Best-effort persistence bootstrap (Cosmos containers)
    try:
        ensure_persistence_setup()
    except Exception:
        pass
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Body Scan Analysis API", version="0.1.0", lifespan=lifespan)
    # Exception handlers
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(scans_router, prefix="/scans", tags=["scans"])
    
    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
