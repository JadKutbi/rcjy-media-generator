# RCJY Media Generator

Royal Commission for Jubail and Yanbu — Communication & Media Department

AI-powered media generation using Google's latest models.

## Features

- **Text** — Articles, social media, press releases, scripts (Gemini 3)
- **Images** — Imagen 4 (Fast/Flagship/Ultra) & Nano Banana (4K)
- **Videos** — Veo 3.1 (up to 148s with extensions, 1080p, with audio)
- **Voice** — Gemini TTS (30+ voices, Flash & Pro)
- **Podcasts** — Multi-speaker episodes from any content
- **Bilingual** — Full English & Arabic UI with RTL support
- **History** — Sidebar panel to browse, download, and manage generated content

## Quick Start (Local)

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-key-here"
streamlit run app.py
```

Get a free API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

## Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io/) and create a new app
3. Select your repo, branch `master`, main file `app.py`
4. Add your API key in **Settings → Secrets**:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
5. Deploy

## Project Structure

```
app.py               # Streamlit UI
generators.py        # Text, image, video, voice, podcast generation
content_extractor.py # URL scraping & file parsing
history.py           # Local file-based history system
rcjy_config.py       # API keys, model IDs, config
requirements.txt     # Dependencies
.streamlit/config.toml  # Theme & server config
```

## License

Internal use — Royal Commission for Jubail and Yanbu.
