# syntax=docker/dockerfile:1.7
# Insights SDK CLI Docker Image
# Multi-stage build optimized for Python CLI applications

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder - Install dependencies and build wheel
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy all files needed for build
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install package with dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install .

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime - Minimal production image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Insights SDK CLI" \
      org.opencontainers.image.description="Python CLI for Palo Alto Networks Prisma Access Insights 3.0 API" \
      org.opencontainers.image.version="0.2.0" \
      org.opencontainers.image.source="https://github.com/ancoleman/insights-sdk-cli"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    INSIGHTS_REGION="americas"

# Create non-root user for security
RUN groupadd --gid 1000 insights && \
    useradd --uid 1000 --gid insights --shell /bin/bash --create-home insights

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
USER insights

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD insights --help > /dev/null 2>&1 || exit 1

ENTRYPOINT ["insights"]
CMD ["--help"]
