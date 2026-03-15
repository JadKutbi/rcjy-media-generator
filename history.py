# Local file-based history for generated content.
# Resets on Streamlit Cloud reboot, persists while app is running.

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("rcjy.history")

BASE_DIR = Path(__file__).parent
HISTORY_DIR = BASE_DIR / "history_data"
HISTORY_FILES_DIR = HISTORY_DIR / "files"
INDEX_FILE = HISTORY_DIR / "index.json"
MAX_ENTRIES = 200

# ID and filename validation
_SAFE_ID_RE = re.compile(r"^[a-f0-9]{16}$")
_SAFE_FILENAME_RE = re.compile(r"^[a-f0-9]{16}\.[a-z0-9]{2,4}$")


def _validate_entry_id(entry_id: str) -> str:
    """Validate that an entry ID is a safe hex string. Prevents path traversal."""
    if not isinstance(entry_id, str) or not _SAFE_ID_RE.match(entry_id):
        raise ValueError(f"Invalid entry ID format: {entry_id!r}")
    return entry_id


def _validate_filename(filename: str) -> str:
    """Validate that a filename matches expected format. Prevents path traversal."""
    if not isinstance(filename, str) or not _SAFE_FILENAME_RE.match(filename):
        raise ValueError(f"Invalid history filename format: {filename!r}")
    return filename


def _safe_filepath(filename: str) -> Path:
    """Resolve a filename to a safe path within HISTORY_FILES_DIR."""
    filename = _validate_filename(filename)
    filepath = (HISTORY_FILES_DIR / filename).resolve()
    # Double-check the resolved path is within the expected directory
    if not str(filepath).startswith(str(HISTORY_FILES_DIR.resolve())):
        raise ValueError(f"Path traversal detected: {filename}")
    return filepath

_EXT_MAP = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "video/mp4": ".mp4",
    "audio/wav": ".wav",
    "audio/mpeg": ".mp3",
    "text/plain": ".txt",
    "text/markdown": ".md",
}


def _ensure_dirs():
    HISTORY_DIR.mkdir(exist_ok=True)
    HISTORY_FILES_DIR.mkdir(exist_ok=True)


def _load_index() -> list[dict]:
    try:
        if INDEX_FILE.exists():
            return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to load history index")
    return []


def _save_index(entries: list[dict]):
    try:
        _ensure_dirs()
        INDEX_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        logger.exception("Failed to save history index")


def is_available() -> bool:
    """Always available — uses local filesystem."""
    try:
        _ensure_dirs()
        return True
    except Exception:
        return False



def save_entry(
    content_type: str,
    prompt: str,
    data,
    mime: str,
    settings: Optional[dict] = None,
    lang: str = "en",
) -> Optional[str]:
    """Save generated content. Returns entry ID or None on failure."""
    try:
        _ensure_dirs()
        entry_id = uuid.uuid4().hex[:16]
        ext = _EXT_MAP.get(mime, ".bin")
        filename = f"{entry_id}{ext}"
        filepath = _safe_filepath(filename)

        # Write file
        if isinstance(data, str):
            filepath.write_text(data, encoding="utf-8")
            file_size = len(data.encode("utf-8"))
        else:
            filepath.write_bytes(data)
            file_size = len(data)

        # Sanitize content_type and lang to prevent index pollution
        _allowed_types = {"text", "image", "video", "voice", "podcast"}
        _allowed_langs = {"en", "ar", "both"}
        content_type = content_type if content_type in _allowed_types else "unknown"
        lang = lang if lang in _allowed_langs else "en"

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

        # Prepend to index
        entries = _load_index()
        entries.insert(0, meta)

        # Auto-prune
        if len(entries) > MAX_ENTRIES:
            for old in entries[MAX_ENTRIES:]:
                try:
                    old_path = _safe_filepath(old.get("filename", ""))
                    if old_path.exists():
                        old_path.unlink()
                except (ValueError, OSError):
                    logger.warning("Could not prune old entry: %s", old.get("id", "?"))
            entries = entries[:MAX_ENTRIES]

        _save_index(entries)
        logger.info("History saved: %s (%s, %s)", entry_id, content_type, format_file_size(file_size))
        return entry_id
    except Exception:
        logger.exception("History save failed")
        return None


def get_entries(content_type: Optional[str] = None, limit: int = 50) -> list[dict]:
    """Return history entries, newest first. Optionally filter by type."""
    try:
        entries = _load_index()
        if content_type:
            entries = [e for e in entries if e.get("type") == content_type]
        return entries[:limit]
    except Exception:
        logger.exception("History get_entries failed")
        return []


def load_file(entry_id: str) -> tuple:
    """Load a generated file. Returns (bytes, mime, filename) or (None, None, None)."""
    try:
        entry_id = _validate_entry_id(entry_id)
        entries = _load_index()
        meta = next((e for e in entries if e["id"] == entry_id), None)
        if meta is None:
            return None, None, None

        filepath = _safe_filepath(meta["filename"])
        if not filepath.exists():
            return None, None, None

        mime = meta.get("mime", "application/octet-stream")
        ext = _EXT_MAP.get(mime, ".bin")
        dl_name = f"rcjy_{meta['type']}_{entry_id[:8]}{ext}"

        if mime.startswith("text/"):
            data = filepath.read_text(encoding="utf-8").encode("utf-8")
        else:
            data = filepath.read_bytes()

        return data, mime, dl_name
    except ValueError as ve:
        logger.warning("Invalid entry_id in load_file: %s", ve)
        return None, None, None
    except Exception:
        logger.exception("History load_file failed: %s", entry_id)
        return None, None, None


def delete_entry(entry_id: str) -> bool:
    """Delete a single history entry."""
    try:
        entry_id = _validate_entry_id(entry_id)
        entries = _load_index()
        meta = next((e for e in entries if e["id"] == entry_id), None)
        if meta:
            try:
                filepath = _safe_filepath(meta["filename"])
                if filepath.exists():
                    filepath.unlink()
            except (ValueError, OSError):
                logger.warning("Could not delete file for entry: %s", entry_id)
            entries = [e for e in entries if e["id"] != entry_id]
            _save_index(entries)
            logger.info("History deleted: %s", entry_id)
            return True
        return False
    except ValueError as ve:
        logger.warning("Invalid entry_id in delete_entry: %s", ve)
        return False
    except Exception:
        logger.exception("History delete failed: %s", entry_id)
        return False


def clear_all() -> int:
    """Delete all history entries. Returns count deleted."""
    try:
        entries = _load_index()
        count = len(entries)
        for e in entries:
            try:
                filepath = _safe_filepath(e.get("filename", ""))
                if filepath.exists():
                    filepath.unlink()
            except (ValueError, OSError):
                logger.warning("Could not delete file during clear: %s", e.get("id", "?"))
        _save_index([])
        logger.info("History cleared: %d entries", count)
        return count
    except Exception:
        logger.exception("History clear_all failed")
        return 0


def get_stats() -> dict:
    """Return history stats: total count, total size, count by type."""
    try:
        entries = _load_index()
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


# helpers

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
