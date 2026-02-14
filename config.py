import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "generated_outputs"
ASSETS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# API key resolution: env var -> streamlit secrets -> .env file
def get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets and st.secrets.get("GEMINI_API_KEY"):
            return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        pass
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val and val != "your_gemini_api_key_here":
                    os.environ["GEMINI_API_KEY"] = val
                    return val
    return ""


def require_api_key() -> str:
    key = get_api_key()
    if not key:
        raise ValueError(
            "GEMINI_API_KEY not configured. "
            "Set it as an environment variable, in .streamlit/secrets.toml, "
            "or in a .env file in the project root."
        )
    return key


# SOTA model IDs
MODELS = {
    "image": {
        "imagen_fast": "imagen-4.0-fast-generate-001",
        "imagen": "imagen-4.0-generate-001",
        "imagen_ultra": "imagen-4.0-ultra-generate-001",
        "nano_banana": "gemini-2.5-flash-image",
        "nano_banana_pro": "gemini-3-pro-image-preview",
    },
    "video": "veo-3.1-generate-preview",
    "voice": {
        "flash": "gemini-2.5-flash-preview-tts",
        "pro": "gemini-2.5-pro-preview-tts",
    },
    "podcast": "gemini-3-flash-preview",
}

RCJY_LOGO_URL = (
    "https://www.rcjy.gov.sa/documents/5272171/0/"
    "color-logo.png/8a44644a-5216-1eaa-9c2a-99d90dd27c2d"
    "?t=1720515544958"
)

SUPPORTED_FILE_TYPES = [
    "jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "tiff", "tif", "ico",
    "pdf", "docx", "doc", "txt", "md", "rtf",
    "csv", "xlsx", "xls", "pptx", "ppt", "json", "xml", "html", "htm",
    "mp3", "wav", "ogg", "m4a", "flac", "aac", "wma",
    "mp4", "avi", "mov", "mkv", "webm", "wmv", "flv", "mpeg",
]
