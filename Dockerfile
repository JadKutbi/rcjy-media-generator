FROM python:3.12-slim

WORKDIR /app

# System deps (build-essential needed only for pip install, removed after)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Remove build-essential after pip install to reduce attack surface
RUN apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# App code
COPY app.py rcjy_config.py generators.py content_extractor.py history.py ./
COPY .streamlit .streamlit

# Create non-root user for running the application
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Create writable directories for history and outputs, owned by appuser
RUN mkdir -p /app/history_data/files /app/generated_outputs /app/assets \
    && chown -R appuser:appuser /app/history_data /app/generated_outputs /app/assets

# Cloud Run uses PORT env var (default 8080)
ENV PORT=8080
# Disable Python bytecode and enable unbuffered output for logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Switch to non-root user
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/_stcore/health || exit 1

CMD streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableXsrfProtection=true \
    --server.enableCORS=false \
    --browser.gatherUsageStats=false
