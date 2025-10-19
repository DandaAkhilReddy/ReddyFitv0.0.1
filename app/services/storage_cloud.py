from __future__ import annotations

"""Cloud storage adapters. Default to local paths; cloud optional.
"""

from typing import Optional

from app.config import settings


def upload_image_and_get_url(local_path: str, dest_path: str) -> str:
    provider = getattr(settings, "storage_provider", "local")
    if provider == "local":
        # Return file path as URL-like string for local dev
        return local_path
    if provider == "gcs":  # pragma: no cover - optional
        try:
            from google.cloud import storage  # type: ignore
        except Exception as e:
            raise RuntimeError("GCS not available. Install google-cloud-storage or set storage_provider=local.") from e
        client = storage.Client(project=settings.gcp_project_id)
        bucket = client.bucket(settings.gcs_bucket_name)  # type: ignore[attr-defined]
        blob = bucket.blob(dest_path)
        blob.upload_from_filename(local_path, content_type="image/jpeg")
        url = blob.generate_signed_url(version="v4", expiration=3600, method="GET")
        return url
    if provider == "azure":  # pragma: no cover - optional
        try:
            from azure.storage.blob import BlobServiceClient, ContentSettings  # type: ignore
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions  # type: ignore
        except Exception as e:
            raise RuntimeError("Azure Storage SDK not available. Install azure-storage-blob or set storage_provider=local.") from e
        conn = settings.azure_storage_connection_string
        container = settings.azure_storage_container
        if not (conn and container):
            raise RuntimeError("Missing Azure storage settings: azure_storage_connection_string, azure_storage_container")
        bsc = BlobServiceClient.from_connection_string(conn)
        cont = bsc.get_container_client(container)
        try:
            cont.create_container()
        except Exception:
            pass
        blob = cont.get_blob_client(dest_path)
        with open(local_path, "rb") as f:
            blob.upload_blob(f, overwrite=True, content_settings=ContentSettings(content_type="image/jpeg"))
        # Build URL (try SAS with account key; fallback to public URL)
        from datetime import datetime, timedelta
        from urllib.parse import quote

        account_name = bsc.account_name
        # Parse account key from connection string
        account_key = None
        try:
            parts = dict(
                kv.split("=", 1) for kv in conn.split(";") if "=" in kv
            )
            account_key = parts.get("AccountKey")
        except Exception:
            account_key = None

        if account_key:
            expiry = datetime.utcnow() + timedelta(minutes=int(settings.azure_sas_expiry_minutes))
            sas = generate_blob_sas(
                account_name=account_name,
                container_name=container,
                blob_name=dest_path,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=expiry,
            )
            return f"https://{account_name}.blob.core.windows.net/{container}/{quote(dest_path)}?{sas}"
        # Fallback (container must be public for this to work)
        return f"https://{account_name}.blob.core.windows.net/{container}/{quote(dest_path)}"
    # Other providers can be added here (s3, azure)
    return local_path
