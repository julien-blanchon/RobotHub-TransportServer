# Multi-stage Dockerfile for LeRobot Arena Transport Server
# Stage 1: Build frontend with Bun (client library + demo)
FROM oven/bun:1-alpine AS frontend-builder

WORKDIR /app

# Install git for dependencies that might need it
RUN apk add --no-cache git

# Copy all JavaScript/TypeScript files
COPY client/js/ ./client/js/
COPY demo/ ./demo/

# Build and link client library
WORKDIR /app/client/js
RUN bun install
RUN bun run build
RUN bun link

# Build demo with linked client library
WORKDIR /app/demo
RUN bun link lerobot-arena-client
RUN bun install
RUN bun run build

# Stage 2: Python backend with uv
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install system dependencies needed for video processing
RUN apt-get update && apt-get install -y \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set up a new user named "user" with user ID 1000 (required for HF Spaces)
RUN useradd -m -u 1000 user

# Switch to the "user" user
USER user

# Set home to the user's home directory
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set the working directory to the user's home directory
WORKDIR $HOME/app

# Copy Python project files for dependency resolution
COPY --chown=user server/pyproject.toml server/uv.lock* ./server/

# Install dependencies first (better caching)
WORKDIR $HOME/app/server
RUN uv sync --no-install-project

# Copy the rest of the Python backend
COPY --chown=user server/ ./

# Install the project itself
RUN uv sync

# Copy built frontend from previous stage with proper ownership
COPY --chown=user --from=frontend-builder /app/demo/build $HOME/app/static-frontend

# Set working directory back to app root
WORKDIR $HOME/app

# Expose port 7860 (HF Spaces default)
EXPOSE 7860

# Start the FastAPI server (serves both frontend and backend)
CMD ["sh", "-c", "cd server && SERVE_FRONTEND=true uv run python launch_with_ui.py"] 