FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run unprivileged; data/ holds uploaded document originals (UPLOAD_DIR).
RUN useradd --create-home --uid 1000 app && mkdir -p data/uploads && chown -R app:app data
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Alembic migrations run in the app's lifespan hook.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
