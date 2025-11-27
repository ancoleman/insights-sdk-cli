# syntax=docker/dockerfile:1.7
# ═══════════════════════════════════════════════════════════════════════════════
# Insights SDK CLI Docker Image
# Multi-stage build optimized for Python CLI applications
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder - Install dependencies and build wheel
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Prevent Python from writing bytecode and buffering stdout/stderr
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

# Copy only dependency files first for better caching
COPY pyproject.toml ./

# Install dependencies using BuildKit cache mount for pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install .

# Copy source code and install the package
COPY src/ ./src/
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install . --no-deps

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime - Minimal production image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Labels for image metadata
LABEL org.opencontainers.image.title="Insights SDK CLI" \
      org.opencontainers.image.description="Python CLI for Palo Alto Networks Prisma Access Insights 3.0 API" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.vendor="Palo Alto Networks" \
      org.opencontainers.image.source="https://github.com/your-org/insights-sdk"

# Security: Run as non-root user
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Default region for API calls
    INSIGHTS_REGION="americas"

# Create non-root user for security
RUN groupadd --gid 1000 insights && \
    useradd --uid 1000 --gid insights --shell /bin/bash --create-home insights

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Switch to non-root user
USER insights

# Health check - verify CLI is functional
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD insights --help > /dev/null 2>&1 || exit 1

# Default entrypoint is the CLI
ENTRYPOINT ["insights"]

# Default command shows help
CMD ["--help"]
