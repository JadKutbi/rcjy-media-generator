# RCJY Media Generator

Royal Commission for Jubail and Yanbu — Communication & Media Department

AI-powered media generation using SOTA models: Imagen 4, Nano Banana, Veo 3.1, Gemini TTS, Gemini 3.

## Features

- **Images** — Imagen 4 (Fast/Flagship/Ultra) & Nano Banana (4K)
- **Videos** — Veo 3.1 (up to 8s, 1080p, with audio)
- **Voice** — Gemini TTS / Chirp 3 (30+ voices, Flash & Pro)
- **Podcasts** — NotebookLM-style multi-speaker from any content
- **Bilingual** — Full English & Arabic UI with RTL support
- **Input** — Text, URLs, files (PDF, DOCX, PPTX, XLSX, CSV, images, audio, video)

## Quick Start (Local)

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-key-here"
streamlit run app.py
```

Get a free API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

## Deploy to Google Cloud Run

### Prerequisites

- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed
- A GCP project with billing enabled

### Steps

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

# Build and deploy in one command
gcloud run deploy rcjy-media \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your-key-here \
  --memory 2Gi \
  --timeout 900 \
  --port 8080
```

That's it. Cloud Run will build the Docker image and deploy. You'll get a URL like `https://rcjy-media-xxxxx.run.app`.

### Update

```bash
gcloud run deploy rcjy-media --source . --region us-central1
```

### Private access (recommended for production)

Remove `--allow-unauthenticated` and use [IAP](https://cloud.google.com/iap) or [Identity-Aware Proxy](https://cloud.google.com/iap/docs/enabling-cloud-run) for access control.

## Project Structure

```
media/
├── app.py                 # Streamlit UI
├── config.py              # API keys, model IDs, file types
├── generators.py          # Image, video, voice, podcast logic
├── content_extractor.py   # URL scraping & file parsing
├── requirements.txt       # Dependencies
├── Dockerfile             # Cloud Run container
├── .dockerignore
├── .gitignore
├── .streamlit/config.toml # Theme & server config
├── .env.example           # API key template
├── run.bat                # Windows launcher
└── RCJY_Media_Generator_Colab.ipynb
```

## License

Internal use — Royal Commission for Jubail and Yanbu.
