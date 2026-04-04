# GCS-backed history storage

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from google.api_core.exceptions import PreconditionFailed, NotFound
from google.cloud import storage

from rcjy_config import GCS_HISTORY_BUCKET

logger = logging.getLogger("rcjy.history")

INDEX_BLOB = "rcjy-media-history/index.json"
FILES_PREFIX = "rcjy-media-history/files/"
MAX_ENTRIES = 200
MAX_RETRIES = 3

# ID format
_SAFE_ID_RE = re.compile(r"^[a-f0-9]{16}$")

_EXT_MAP = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "video/mp4": ".mp4",
    "audio/wav": ".wav",
    "audio/mpeg": ".mp3",
    "text/plain": ".txt",
    "text/markdown": ".md",
}

_ALLOWED_TYPES = {"text", "image", "video", "voice", "podcast"}
_ALLOWED_LANGS = {"en", "ar", "both"}

# GCS client cache
_gcs_client = None
_bucket = None


def _validate_entry_id(entry_id: str) -> str:
    # Validate entry ID format
    if not isinstance(entry_id, str) or not _SAFE_ID_RE.match(entry_id):
        raise ValueError(f"Invalid entry ID format: {entry_id!r}")
    return entry_id


def _get_bucket():
    # Get cached GCS bucket
    global _gcs_client, _bucket
    if _bucket is not None:
        return _bucket
    _gcs_client = storage.Client()
    _bucket = _gcs_client.bucket(GCS_HISTORY_BUCKET)
    return _bucket


def _load_index() -> tuple[list[dict], int]:
    # Load index from GCS with generation for concurrency control
    try:
        bucket = _get_bucket()
        blob = bucket.blob(INDEX_BLOB)
        # Download with generation info
        content = blob.download_as_text(encoding="utf-8")
        generation = blob.generation
        return json.loads(content), generation
    except NotFound:
        return [], 0
    except Exception:
        logger.exception("Failed to load history index from GCS")
        return [], 0


def _save_index(entries: list[dict], expected_generation: int) -> bool:
    # Save index with optimistic concurrency
    bucket = _get_bucket()
    blob = bucket.blob(INDEX_BLOB)
    data = json.dumps(entries, ensure_ascii=False, indent=1)
    try:
        blob.upload_from_string(
            data,
            content_type="application/json",
            if_generation_match=expected_generation,
        )
        return True
    except PreconditionFailed:
        # Another instance updated the index concurrently
        return False


def is_available() -> bool:
    # Check if GCS bucket is accessible
    try:
        bucket = _get_bucket()
        bucket.exists()
        return True
    except Exception:
        logger.exception("GCS bucket not accessible")
        return False


def save_entry(
    content_type: str,
    prompt: str,
    data,
    mime: str,
    settings: Optional[dict] = None,
    lang: str = "en",
) -> Optional[str]:
    # Save generated content to GCS
    try:
        entry_id = uuid.uuid4().hex[:16]
        ext = _EXT_MAP.get(mime, ".bin")
        filename = f"{entry_id}{ext}"
        blob_name = f"{FILES_PREFIX}{filename}"

        # Upload file
        bucket = _get_bucket()
        file_blob = bucket.blob(blob_name)

        if isinstance(data, str):
            file_blob.upload_from_string(data, content_type=mime)
            file_size = len(data.encode("utf-8"))
        else:
            file_blob.upload_from_string(data, content_type=mime)
            file_size = len(data)

        # Sanitize
        content_type = content_type if content_type in _ALLOWED_TYPES else "unknown"
        lang = lang if lang in _ALLOWED_LANGS else "en"

        # Build metadata
        now = datetime.now(timezone.utc)
        meta = {
            "id": entry_id,
            "type": content_type,
            "prompt": prompt[:500],
            "mime": mime,
            "filename": filename,
            "file_size": file_size,
            "settings": settings or {},
            "lang": lang,
            "created_at": now.isoformat(),
            "preview": (data[:300] if isinstance(data, str) else ""),
        }

        # Retry loop for index update
        for attempt in range(MAX_RETRIES):
            entries, generation = _load_index()
            entries.insert(0, meta)

            # Prune old entries
            if len(entries) > MAX_ENTRIES:
                for old in entries[MAX_ENTRIES:]:
                    _delete_file_blob(old.get("filename", ""))
                entries = entries[:MAX_ENTRIES]

            if _save_index(entries, generation):
                logger.info("History saved: %s (%s, %s)", entry_id, content_type, format_file_size(file_size))
                return entry_id

            logger.warning("Index conflict on save (attempt %d), retrying", attempt + 1)

        # All retries failed, clean up
        logger.error("Failed to update index after %d retries", MAX_RETRIES)
        file_blob.delete()
        return None
    except Exception:
        logger.exception("History save failed")
        return None


def get_entries(content_type: Optional[str] = None, limit: int = 50) -> list[dict]:
    # Return history entries, newest first
    try:
        entries, _ = _load_index()
        if content_type:
            entries = [e for e in entries if e.get("type") == content_type]
        return entries[:limit]
    except Exception:
        logger.exception("History get_entries failed")
        return []


def load_file(entry_id: str) -> tuple:
    # Load generated file from GCS
    try:
        entry_id = _validate_entry_id(entry_id)
        entries, _ = _load_index()
        meta = next((e for e in entries if e["id"] == entry_id), None)
        if meta is None:
            return None, None, None

        blob_name = f"{FILES_PREFIX}{meta['filename']}"
        bucket = _get_bucket()
        blob = bucket.blob(blob_name)

        if not blob.exists():
            return None, None, None

        mime = meta.get("mime", "application/octet-stream")
        ext = _EXT_MAP.get(mime, ".bin")
        dl_name = f"rcjy_{meta['type']}_{entry_id[:8]}{ext}"

        data = blob.download_as_bytes()
        return data, mime, dl_name
    except ValueError as ve:
        logger.warning("Invalid entry_id in load_file: %s", ve)
        return None, None, None
    except Exception:
        logger.exception("History load_file failed: %s", entry_id)
        return None, None, None


def delete_entry(entry_id: str) -> bool:
    # Delete single history entry
    try:
        entry_id = _validate_entry_id(entry_id)

        for attempt in range(MAX_RETRIES):
            entries, generation = _load_index()
            meta = next((e for e in entries if e["id"] == entry_id), None)
            if meta is None:
                return False

            _delete_file_blob(meta.get("filename", ""))
            entries = [e for e in entries if e["id"] != entry_id]

            if _save_index(entries, generation):
                logger.info("History deleted: %s", entry_id)
                return True

            logger.warning("Index conflict on delete (attempt %d), retrying", attempt + 1)

        return False
    except ValueError as ve:
        logger.warning("Invalid entry_id in delete_entry: %s", ve)
        return False
    except Exception:
        logger.exception("History delete failed: %s", entry_id)
        return False


def clear_all() -> int:
    # Delete all history entries
    try:
        for attempt in range(MAX_RETRIES):
            entries, generation = _load_index()
            count = len(entries)
            if count == 0:
                return 0

            # Delete all blobs
            for e in entries:
                _delete_file_blob(e.get("filename", ""))

            if _save_index([], generation):
                logger.info("History cleared: %d entries", count)
                return count

            logger.warning("Index conflict on clear (attempt %d), retrying", attempt + 1)

        return 0
    except Exception:
        logger.exception("History clear_all failed")
        return 0


def get_stats() -> dict:
    # Return history stats
    try:
        entries, _ = _load_index()
        total = len(entries)
        total_size = sum(e.get("file_size", 0) for e in entries)
        by_type = {}
        for e in entries:
            t = e.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        return {"total": total, "total_size": total_size, "by_type": by_type}
    except Exception:
        logger.exception("History get_stats failed")
        return {"total": 0, "total_size": 0, "by_type": {}}



def _delete_file_blob(filename: str):
    # Delete file blob, ignore if missing
    if not filename:
        return
    try:
        blob_name = f"{FILES_PREFIX}{filename}"
        bucket = _get_bucket()
        bucket.blob(blob_name).delete()
    except NotFound:
        pass
    except Exception:
        logger.warning("Could not delete blob: %s", filename)


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_timestamp(iso_str: str, lang: str = "en") -> str:
    # Human-readable relative timestamp
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
