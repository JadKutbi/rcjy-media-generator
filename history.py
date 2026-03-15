"""Cloud Datastore-backed history for generated content.

Uses Google Cloud Datastore (which the user has Owner access to).

Entities:
  Kind "HistoryEntry"  — metadata (prompt, type, settings, timestamps)
  Kind "HistoryChunk"  — file data stored in ≤900 KB chunks, parent=HistoryEntry

Files up to 20 MB are stored. Larger files get metadata-only (no re-download).
Graceful fallback: every public function returns a safe default if Datastore
is unavailable, so the app never crashes because of history.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("rcjy.history")

PROJECT_ID = "rcjy-ai-shared-services-proj"
MAX_ENTRIES = 200
CHUNK_SIZE = 900_000  # 900 KB per chunk (under 1 MB entity limit)
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB — skip file storage above this

_EXT_MAP = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "video/mp4": ".mp4",
    "audio/wav": ".wav",
    "audio/mpeg": ".mp3",
    "text/plain": ".txt",
    "text/markdown": ".md",
}

# ── lazy Datastore client ────────────────────────────────────────────────────
_client = None
_client_checked = False


def _get_client():
    """Return the Datastore client, or None if unavailable.

    Auth priority:
      1. Streamlit secrets  (gcp_service_account section)
      2. Default credentials (Cloud Run, GOOGLE_APPLICATION_CREDENTIALS, etc.)
    """
    global _client, _client_checked
    if not _client_checked:
        _client_checked = True
        try:
            from google.cloud import datastore

            # Try Streamlit secrets first (for Streamlit Cloud deployment)
            try:
                import streamlit as st
                if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
                    from google.oauth2 import service_account
                    creds = service_account.Credentials.from_service_account_info(
                        dict(st.secrets["gcp_service_account"])
                    )
                    _client = datastore.Client(project=PROJECT_ID, credentials=creds)
                    logger.info("Datastore: using Streamlit secrets credentials")
                else:
                    raise KeyError("no streamlit secrets")
            except Exception:
                # Fall back to default credentials (Cloud Run, env var, etc.)
                _client = datastore.Client(project=PROJECT_ID)

            # Quick connectivity check
            q = _client.query(kind="HistoryEntry")
            q.keys_only()
            list(q.fetch(limit=1))
            logger.info("Datastore history connected: %s", PROJECT_ID)
        except Exception as e:
            logger.warning("Datastore history unavailable: %s", e)
            _client = None
    return _client


def is_available() -> bool:
    """True if Datastore is reachable."""
    return _get_client() is not None


# ── public API ───────────────────────────────────────────────────────────────

def save_entry(
    content_type: str,
    prompt: str,
    data,
    mime: str,
    settings: Optional[dict] = None,
    lang: str = "en",
) -> Optional[str]:
    """Save generated content to Datastore. Returns entry ID or None on failure."""
    client = _get_client()
    if client is None:
        return None
    try:
        entry_id = uuid.uuid4().hex[:16]

        # Prepare file bytes
        if isinstance(data, str):
            file_bytes = data.encode("utf-8")
        else:
            file_bytes = data
        file_size = len(file_bytes)
        file_stored = file_size <= MAX_FILE_SIZE

        # Save metadata entity
        now = datetime.now(timezone.utc)
        key = client.key("HistoryEntry", entry_id)
        entity = client.entity(key=key)
        entity.update({
            "type": content_type,
            "prompt": prompt[:500],
            "mime": mime,
            "file_size": file_size,
            "file_stored": file_stored,
            "settings": settings or {},
            "lang": lang,
            "created_at": now,
            "preview": (data[:300] if isinstance(data, str) else ""),
        })
        entity.exclude_from_indexes = ("prompt", "preview", "settings")
        client.put(entity)

        # Save file in chunks
        if file_stored:
            for i in range(0, file_size, CHUNK_SIZE):
                chunk_key = client.key("HistoryEntry", entry_id, "HistoryChunk", i // CHUNK_SIZE)
                chunk_entity = client.entity(key=chunk_key)
                chunk_entity["data"] = file_bytes[i:i + CHUNK_SIZE]
                chunk_entity["index"] = i // CHUNK_SIZE
                chunk_entity.exclude_from_indexes = ("data",)
                client.put(chunk_entity)

        logger.info("History saved: %s (%s, %s, %s)",
                     entry_id, content_type, format_file_size(file_size),
                     "stored" if file_stored else "metadata-only")
        _auto_prune(client)
        return entry_id
    except Exception:
        logger.exception("History save failed")
        return None


def get_entries(content_type: Optional[str] = None, limit: int = 50) -> list[dict]:
    """Return history entries, newest first. Optionally filter by type."""
    client = _get_client()
    if client is None:
        return []
    try:
        q = client.query(kind="HistoryEntry")
        if content_type:
            q.add_filter("type", "=", content_type)
        q.order = ["-created_at"]

        results = []
        for entity in q.fetch(limit=limit):
            results.append({
                "id": entity.key.name,
                "type": entity.get("type", ""),
                "prompt": entity.get("prompt", ""),
                "mime": entity.get("mime", ""),
                "file_size": entity.get("file_size", 0),
                "file_stored": entity.get("file_stored", False),
                "settings": entity.get("settings", {}),
                "lang": entity.get("lang", "en"),
                "created_at": entity.get("created_at", ""),
                "preview": entity.get("preview", ""),
            })
        # Convert datetime to isoformat strings
        for r in results:
            if hasattr(r["created_at"], "isoformat"):
                r["created_at"] = r["created_at"].isoformat()
        return results
    except Exception:
        logger.exception("History get_entries failed")
        return []


def load_file(entry_id: str) -> tuple:
    """Download a generated file. Returns (bytes, mime, filename) or (None, None, None)."""
    client = _get_client()
    if client is None:
        return None, None, None
    try:
        key = client.key("HistoryEntry", entry_id)
        entity = client.get(key)
        if entity is None:
            return None, None, None
        if not entity.get("file_stored", False):
            return None, None, None

        mime = entity.get("mime", "application/octet-stream")
        content_type = entity.get("type", "file")
        ext = _EXT_MAP.get(mime, ".bin")
        filename = f"rcjy_{content_type}_{entry_id[:8]}{ext}"

        # Reassemble chunks
        q = client.query(kind="HistoryChunk", ancestor=key)
        q.order = ["index"]
        chunks = sorted(q.fetch(), key=lambda c: c.get("index", 0))
        file_bytes = b"".join(bytes(c["data"]) for c in chunks)

        return file_bytes, mime, filename
    except Exception:
        logger.exception("History load_file failed: %s", entry_id)
        return None, None, None


def delete_entry(entry_id: str) -> bool:
    """Delete a single history entry (metadata + chunks)."""
    client = _get_client()
    if client is None:
        return False
    try:
        key = client.key("HistoryEntry", entry_id)
        # Delete chunks first
        q = client.query(kind="HistoryChunk", ancestor=key)
        q.keys_only()
        chunk_keys = [e.key for e in q.fetch()]
        if chunk_keys:
            client.delete_multi(chunk_keys)
        # Delete metadata
        client.delete(key)
        logger.info("History deleted: %s", entry_id)
        return True
    except Exception:
        logger.exception("History delete failed: %s", entry_id)
        return False


def clear_all() -> int:
    """Delete all history entries. Returns count deleted."""
    client = _get_client()
    if client is None:
        return 0
    try:
        # Delete all chunks
        q = client.query(kind="HistoryChunk")
        q.keys_only()
        chunk_keys = [e.key for e in q.fetch()]
        if chunk_keys:
            for i in range(0, len(chunk_keys), 500):
                client.delete_multi(chunk_keys[i:i + 500])

        # Delete all entries
        q = client.query(kind="HistoryEntry")
        q.keys_only()
        entry_keys = [e.key for e in q.fetch()]
        count = len(entry_keys)
        if entry_keys:
            for i in range(0, len(entry_keys), 500):
                client.delete_multi(entry_keys[i:i + 500])

        logger.info("History cleared: %d entries", count)
        return count
    except Exception:
        logger.exception("History clear_all failed")
        return 0


def get_stats() -> dict:
    """Return history stats: total count, total size, count by type."""
    client = _get_client()
    if client is None:
        return {"total": 0, "total_size": 0, "by_type": {}}
    try:
        q = client.query(kind="HistoryEntry")
        total = 0
        total_size = 0
        by_type = {}
        for entity in q.fetch():
            total += 1
            total_size += entity.get("file_size", 0)
            t = entity.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        return {"total": total, "total_size": total_size, "by_type": by_type}
    except Exception:
        logger.exception("History get_stats failed")
        return {"total": 0, "total_size": 0, "by_type": {}}


# ── helpers ──────────────────────────────────────────────────────────────────

def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_timestamp(iso_str: str, lang: str = "en") -> str:
    """Return a human-readable relative timestamp."""
    try:
        if isinstance(iso_str, datetime):
            dt = iso_str
        else:
            dt = datetime.fromisoformat(str(iso_str))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = datetime.now(timezone.utc) - dt
        secs = int(diff.total_seconds())
        if secs < 60:
            return "الآن" if lang == "ar" else "Just now"
        if secs < 3600:
            m = secs // 60
            return f"منذ {m} د" if lang == "ar" else f"{m}m ago"
        if secs < 86400:
            h = secs // 3600
            return f"منذ {h} س" if lang == "ar" else f"{h}h ago"
        d = secs // 86400
        return f"منذ {d} ي" if lang == "ar" else f"{d}d ago"
    except Exception:
        return str(iso_str)[:16]


def _auto_prune(client):
    """Delete oldest entries if count exceeds MAX_ENTRIES."""
    try:
        q = client.query(kind="HistoryEntry")
        q.order = ["created_at"]
        entries = list(q.fetch())
        if len(entries) <= MAX_ENTRIES:
            return
        to_delete = entries[:len(entries) - MAX_ENTRIES]
        for entity in to_delete:
            delete_entry(entity.key.name)
        logger.info("Auto-pruned %d old entries", len(to_delete))
    except Exception:
        logger.exception("Auto-prune failed")
