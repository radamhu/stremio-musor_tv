# Python-based Stremio HU Live Movies Addon
# Multi-stage build with optimized Docker layer caching

# Stage 1: Base image with system dependencies
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies for Playwright (cached unless apt packages change)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies installation
FROM base AS dependencies

# Copy only requirements file first (cached unless requirements.txt changes)
COPY requirements.txt .

# Install Python dependencies with pip cache mount for faster rebuilds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (cached in separate layers)
RUN playwright install chromium
RUN playwright install-deps chromium

# Stage 3: Final runtime image
FROM dependencies AS runtime

# Copy application code (only invalidates cache when source code changes)
COPY src/ ./

# Expose port
EXPOSE 7000

# Set environment variables
ENV PORT=7000
ENV LOG_LEVEL=info
ENV CACHE_TTL_MIN=10
ENV SCRAPE_RATE_MS=30000
ENV TZ=Europe/Budapest

# Run the application
CMD ["python", "main.py"]
