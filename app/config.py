from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = Field("local", description="Deployment environment")
    data_dir: str = Field(".data", description="Local data dir for images/results in local mode")

    # Anthropic (Claude)
    anthropic_api_key: str | None = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model_vision: str = Field(
        "claude-3-5-sonnet-20240620",
        description="Claude model for vision analysis",
    )

    # Image thresholds
    image_min_width: int = 480
    image_min_height: int = 640
    image_max_width: int = 6000
    image_max_height: int = 6000
    image_min_size_bytes: int = 100_000
    image_max_size_bytes: int = 10_000_000
    sharpness_threshold: float = 50.0
    preprocess_max_dim: int = 1024
    jpeg_quality: int = 85
    image_quality_min_score: float = 50.0

    # Analysis thresholds
    confidence_threshold: float = 0.70
    pipeline_version: str = "v0.1"
    angle_enforcement: bool = False

    # Storage providers: local | gcs | azure
    storage_provider: str = Field("local", description="Where to store images/URLs")
    # Azure Storage
    azure_storage_connection_string: str | None = None
    azure_storage_container: str | None = None
    azure_sas_expiry_minutes: int = 60

    # Firestore/Cloud (stubs for local)
    gcp_project_id: str | None = None
    firestore_enabled: bool = False
    gcs_bucket_name: str | None = None

    # Azure Cosmos DB (optional)
    cosmos_enabled: bool = False
    cosmos_endpoint: str | None = None
    cosmos_key: str | None = None
    cosmos_db: str | None = None
    cosmos_scans_container: str = "scans"
    cosmos_users_container: str = "users"

    # WHOOP/Terra
    whoop_enabled: bool = False
    terra_enabled: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
