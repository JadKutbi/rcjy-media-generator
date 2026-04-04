import uuid
from datetime import datetime, timezone
from typing import Optional

import streamlit as st

MAX_ENTRIES = 100

_EXT_MAP = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "video/mp4": ".mp4",
    "audio/wav": ".wav",
    "audio/mpeg": ".mp3",
    "text/plain": ".txt",
    "text/markdown": ".md",
}


def _get_store() -> dict:
    if "_local_history" not in st.session_state:
        st.session_state["_local_history"] = {"entries": [], "files": {}}
    return st.session_state["_local_history"]


def is_available() -> bool:
    return True


def save_entry(
    content_type: str,
    prompt: str,
    data,
    mime: str,
    settings: Optional[dict] = None,
    lang: str = "en",
) -> Optional[str]:
    store = _get_store()
    entry_id = uuid.uuid4().hex[:16]
    ext = _EXT_MAP.get(mime, ".bin")
    filename = f"{entry_id}{ext}"

    if isinstance(data, str):
        file_size = len(data.encode("utf-8"))
    else:
        file_size = len(data)

    meta = {
        "id": entry_id,
        "type": content_type,
        "prompt": prompt[:500],
        "mime": mime,
        "filename": filename,
        "file_size": file_size,
        "settings": settings or {},
        "lang": lang,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "preview": (data[:300] if isinstance(data, str) else ""),
    }

    store["entries"].insert(0, meta)
    store["files"][entry_id] = data

    if len(store["entries"]) > MAX_ENTRIES:
        for old in store["entries"][MAX_ENTRIES:]:
            store["files"].pop(old["id"], None)
        store["entries"] = store["entries"][:MAX_ENTRIES]

    return entry_id


def get_entries(content_type: Optional[str] = None, limit: int = 50) -> list[dict]:
    store = _get_store()
    entries = store["entries"]
    if content_type:
        entries = [e for e in entries if e.get("type") == content_type]
    return entries[:limit]


def load_file(entry_id: str) -> tuple:
    store = _get_store()
    meta = next((e for e in store["entries"] if e["id"] == entry_id), None)
    if meta is None:
        return None, None, None
    data = store["files"].get(entry_id)
    if data is None:
        return None, None, None
    mime = meta.get("mime", "application/octet-stream")
    ext = _EXT_MAP.get(mime, ".bin")
    dl_name = f"rcjy_{meta['type']}_{entry_id[:8]}{ext}"
    return data, mime, dl_name


def delete_entry(entry_id: str) -> bool:
    store = _get_store()
    meta = next((e for e in store["entries"] if e["id"] == entry_id), None)
    if meta is None:
        return False
    store["entries"] = [e for e in store["entries"] if e["id"] != entry_id]
    store["files"].pop(entry_id, None)
    return True


def clear_all() -> int:
    store = _get_store()
    count = len(store["entries"])
    store["entries"] = []
    store["files"] = {}
    return count


def get_stats() -> dict:
    store = _get_store()
    entries = store["entries"]
    total = len(entries)
    total_size = sum(e.get("file_size", 0) for e in entries)
    by_type = {}
    for e in entries:
        t = e.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {"total": total, "total_size": total_size, "by_type": by_type}


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_timestamp(iso_str: str, lang: str = "en") -> str:
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
