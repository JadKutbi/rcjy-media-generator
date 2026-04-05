import atexit
import json
import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "generated_outputs"
ASSETS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# GCP config
GCP_PROJECT = os.getenv("GCP_PROJECT", "rcjy-ai-shared-services-proj")
GCP_LOCATION = os.getenv("GCP_LOCATION", "me-central2")

# GCS bucket
GCS_HISTORY_BUCKET = os.getenv("GCS_HISTORY_BUCKET", "rcjy-ai-shared-services-storage")

# API key resolution
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


# Vertex AI client

_creds_setup_done = False


def _cleanup_temp_creds():
    # Remove temp credentials file on shutdown
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if path and os.path.basename(path).startswith("gcp_sa_"):
        try:
            os.remove(path)
        except OSError:
            pass


def _setup_gcp_credentials():
    # Write GCP service account JSON from Streamlit secrets to temp file
    global _creds_setup_done
    if _creds_setup_done or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    _creds_setup_done = True
    try:
        import streamlit as st
        sa = st.secrets.get("gcp_service_account")
        if sa:
            sa_dict = dict(sa)
            fd, path = tempfile.mkstemp(suffix=".json", prefix="gcp_sa_")
            os.chmod(path, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump(sa_dict, f)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
            atexit.register(_cleanup_temp_creds)
    except Exception:
        pass


def has_credentials() -> bool:
    # Check if credentials are available
    _setup_gcp_credentials()
    # Cloud Run ADC or explicit creds
    if os.environ.get("K_SERVICE") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return True
    return bool(get_api_key())


_genai_client = None


def get_genai_client():
    # Get genai client: API key first, fallback to Vertex AI
    global _genai_client
    if _genai_client is not None:
        return _genai_client

    from google import genai

    # Prefer API key
    key = get_api_key()
    if key:
        _genai_client = genai.Client(api_key=key)
        return _genai_client

    _setup_gcp_credentials()

    # Fallback to Vertex AI
    if os.environ.get("K_SERVICE") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            _genai_client = genai.Client(
                vertexai=True,
                project=GCP_PROJECT,
                location=GCP_LOCATION,
            )
            return _genai_client
        except Exception:
            pass

    raise ValueError(
        "No credentials found. Set GEMINI_API_KEY, or on Cloud Run attach a service account "
        "with Vertex AI User role, or locally run 'gcloud auth application-default login'."
    )


# Models
MODELS = {
    "image": {
        "imagen_fast": "imagen-4.0-fast-generate-001",
        "imagen": "imagen-4.0-generate-001",
        "imagen_ultra": "imagen-4.0-ultra-generate-001",
        "gemini_flash": "gemini-2.0-flash-preview-image-generation",
        "gemini_pro": "gemini-2.0-flash-exp",
    },
    "video": {
        "standard": "veo-3.1-generate-preview",
        "fast": "veo-3.1-fast-generate-preview",
    },
    "voice": {
        "flash": "gemini-2.5-flash-preview-tts",
        "pro": "gemini-2.5-pro-preview-tts",
    },
    "podcast": "gemini-3-flash-preview",
    "text": {
        "pro": "gemini-3.1-pro-preview",
        "flash": "gemini-3-flash-preview",
    },
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
