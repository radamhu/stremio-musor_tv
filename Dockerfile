# Python-based Stremio HU Live Movies Addon
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy application code
COPY src/ ./

EXPOSE 7000

ENV PORT=7000
ENV LOG_LEVEL=info
ENV CACHE_TTL_MIN=10
ENV SCRAPE_RATE_MS=30000
ENV TZ=Europe/Budapest

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7000} --log-level ${LOG_LEVEL:-info}"]
