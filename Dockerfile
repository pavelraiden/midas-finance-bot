FROM python:3.11-slim

LABEL maintainer="Midas Financial Bot"
LABEL description="Telegram bot for financial tracking with AI-powered categorization"

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY migrations/ ./migrations/

ENV PYTHONPATH=/app

RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

USER botuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "-m", "src.main"]
