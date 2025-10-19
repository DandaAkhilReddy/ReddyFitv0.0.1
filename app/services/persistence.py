from __future__ import annotations

"""Persistence adapters: Local JSON (default) and optional Firestore transaction.
Switch via settings or feature flags; code only imports cloud SDKs when enabled.
"""

from typing import Any, Dict

from app.config import settings
from app.services.storage import save_scan_local, load_scan_local


def save_scan(scan_id: str, obj: Dict[str, Any]) -> str:
    # Default local
    if getattr(settings, "cosmos_enabled", False):
        return _save_scan_cosmos(scan_id, obj)
    if getattr(settings, "firestore_enabled", False):
        return _save_scan_firestore(scan_id, obj)
    else:
        return save_scan_local(scan_id, obj)
    
def _save_scan_firestore(scan_id: str, obj: Dict[str, Any]) -> str:
    try:  # pragma: no cover
        from google.cloud import firestore  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Firestore not available. Install google-cloud-firestore or disable feature.") from e
    client = firestore.Client(project=settings.gcp_project_id)
    batch = client.batch()
    scan_ref = client.collection("scans").document(scan_id)
    batch.set(scan_ref, obj)
    if obj.get("uid"):
        user_ref = client.collection("users").document(obj["uid"])  # type: ignore
        batch.set(user_ref, {"scanCount": firestore.Increment(1), "lastScanAt": obj.get("createdAt")}, merge=True)
    batch.commit()
    return f"firestore:scans/{scan_id}"

def _save_scan_cosmos(scan_id: str, obj: Dict[str, Any]) -> str:
    try:  # pragma: no cover
        from azure.cosmos import CosmosClient  # type: ignore
        from azure.cosmos.exceptions import CosmosHttpResponseError  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Azure Cosmos SDK not available. Install azure-cosmos or disable cosmos_enabled.") from e
    endpoint = getattr(settings, "cosmos_endpoint", None)
    key = getattr(settings, "cosmos_key", None)
    db_id = getattr(settings, "cosmos_db", None)
    scans_container = getattr(settings, "cosmos_scans_container", "scans")
    users_container = getattr(settings, "cosmos_users_container", "users")
    if not (endpoint and key and db_id):
        raise RuntimeError("Cosmos settings missing: cosmos_endpoint, cosmos_key, cosmos_db")
    client = CosmosClient(endpoint, key)
    db = client.get_database_client(db_id)
    scans = db.get_container_client(scans_container)
    users = db.get_container_client(users_container)
    # Ensure id field present
    item = {**obj}
    item.setdefault("id", scan_id)
    scans.upsert_item(item)
    if obj.get("uid"):
        try:
            users.upsert_item({"id": obj["uid"], "uid": obj["uid"], "lastScanAt": obj.get("createdAt"), "scanCountInc": 1})
        except CosmosHttpResponseError:
            pass
    return f"cosmos:scans/{scan_id}"


def load_scan(scan_id: str) -> Dict[str, Any] | None:
    if getattr(settings, "cosmos_enabled", False):
        try:  # pragma: no cover
            from azure.cosmos import CosmosClient  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("Azure Cosmos SDK not available. Install azure-cosmos or disable cosmos_enabled.") from e
        endpoint = getattr(settings, "cosmos_endpoint", None)
        key = getattr(settings, "cosmos_key", None)
        db_id = getattr(settings, "cosmos_db", None)
        scans_container = getattr(settings, "cosmos_scans_container", "scans")
        client = CosmosClient(endpoint, key)
        db = client.get_database_client(db_id)
        scans = db.get_container_client(scans_container)
        try:
            item = scans.read_item(item=scan_id, partition_key=scan_id)
            return dict(item)
        except Exception:
            return None
    if getattr(settings, "firestore_enabled", False):
        try:  # pragma: no cover
            from google.cloud import firestore  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("Firestore not available. Install google-cloud-firestore or disable feature.") from e
        client = firestore.Client(project=settings.gcp_project_id)
        doc = client.collection("scans").document(scan_id).get()
        return doc.to_dict() if doc.exists else None
    return load_scan_local(scan_id)


def ensure_persistence_setup() -> None:
    """Optionally create Cosmos containers when enabled. No-op on local or Firestore.
    Does not raise on failure; logs are recommended in production.
    """
    if getattr(settings, "cosmos_enabled", False):  # pragma: no cover
        try:
            from azure.cosmos import CosmosClient, PartitionKey  # type: ignore
        except Exception:
            return
        if not (settings.cosmos_endpoint and settings.cosmos_key and settings.cosmos_db):
            return
        client = CosmosClient(settings.cosmos_endpoint, settings.cosmos_key)
        db = client.create_database_if_not_exists(settings.cosmos_db)
        # Create containers if not exist
        db.create_container_if_not_exists(
            id=settings.cosmos_scans_container,
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400,
        )
        db.create_container_if_not_exists(
            id=settings.cosmos_users_container,
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400,
        )
