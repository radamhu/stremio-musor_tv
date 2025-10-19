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
    pip install -r requirements.txt

# Install Playwright browsers (cached in separate layers)
RUN playwright install chromium

# Install Playwright system dependencies with workaround for obsolete packages
# Replace obsolete ttf-* packages with fonts-* equivalents
RUN apt-get update && \
    apt-get install -y fonts-unifont fonts-ubuntu || true && \
    playwright install-deps chromium || apt-get install -y \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

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

# Run the application with uvicorn directly (production-ready)
# Use sh -c to allow environment variable expansion in CMD
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7000} --log-level ${LOG_LEVEL:-info}"]
