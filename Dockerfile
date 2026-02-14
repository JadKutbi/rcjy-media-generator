FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app.py config.py generators.py content_extractor.py ./
COPY .streamlit .streamlit

# Cloud Run uses PORT env var (default 8080)
ENV PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/_stcore/health || exit 1

CMD streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableXsrfProtection=false \
    --server.enableCORS=false \
    --browser.gatherUsageStats=false
