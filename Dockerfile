# Stage 1: Build frontend with Bun (client library + demo)
FROM oven/bun:1-alpine AS frontend-builder

# Build argument for transport server URL
ARG PUBLIC_TRANSPORT_SERVER_URL=https://blanchon-robothub-transportserver.hf.space/api
ENV PUBLIC_TRANSPORT_SERVER_URL=${PUBLIC_TRANSPORT_SERVER_URL}

WORKDIR /app

# Install git for dependencies that might need it
RUN apk add --no-cache git

# Copy package files for better caching
COPY client/js/package.json client/js/tsconfig.json* ./client/js/
COPY demo/package.json demo/tsconfig.json* demo/svelte.config.js* ./demo/

# Install client library dependencies first
WORKDIR /app/client/js
RUN bun install --frozen-lockfile

# Copy client library source code
COPY client/js/src/ ./src/
COPY client/js/bun.lock* ./

# Build the client library
RUN bun run build

# Install demo dependencies
WORKDIR /app/demo
RUN bun install --frozen-lockfile

# Copy demo source code
COPY demo/src/ ./src/
COPY demo/static/ ./static/
COPY demo/vite.config.ts* demo/tailwind.config.* demo/.prettierrc* ./

# Build demo application
RUN bun run build

# Stage 2: Python backend with uv
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set environment variables for Python and UV
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache \
    PORT=8000

# Install system dependencies needed for video processing
RUN apt-get update && apt-get install -y \
    # Build tools for compiling Python packages
    build-essential \
    gcc \
    g++ \
    # Video processing libraries
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    # Additional system libraries
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    pkg-config \
    # FFmpeg for video processing
    ffmpeg \
    # Git for potential model downloads
    git \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user (required for HF Spaces)
RUN groupadd -r appuser && useradd -r -g appuser -m -s /bin/bash -u 1000 appuser

# Set working directory and ensure it's owned by appuser
WORKDIR /app
RUN chown -R appuser:appuser /app

# Switch to appuser before installing dependencies
USER appuser

# Copy dependency files for better layer caching
COPY --chown=appuser:appuser server/pyproject.toml server/uv.lock* ./server/

# Install dependencies first (better caching)
WORKDIR /app/server
RUN --mount=type=cache,target=/tmp/uv-cache,uid=1000,gid=1000 \
    uv sync --locked --no-install-project --no-dev

# Copy the rest of the Python backend
COPY --chown=appuser:appuser server/ ./

# Install the project in non-editable mode for production
RUN --mount=type=cache,target=/tmp/uv-cache,uid=1000,gid=1000 \
    uv sync --locked --no-editable --no-dev

# Copy built frontend from previous stage with proper ownership
COPY --chown=appuser:appuser --from=frontend-builder /app/demo/build /app/static-frontend

# Set working directory back to app root
WORKDIR /app

# Add virtual environment to PATH
ENV PATH="/app/server/.venv/bin:$PATH"

# Expose the configured port (default 8000)
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen(f'http://localhost:${PORT}/health')" || exit 1

# Start the FastAPI server (serves both frontend and backend)
CMD ["sh", "-c", "cd server && SERVE_FRONTEND=true uv run python launch_with_ui.py --host localhost --port ${PORT}"] 