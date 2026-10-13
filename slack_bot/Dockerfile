FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/

RUN useradd --create-home --uid 1000 app
USER app

# main.py imports its siblings by bare name, so run it as a script from src/.
CMD ["python", "src/main.py"]
