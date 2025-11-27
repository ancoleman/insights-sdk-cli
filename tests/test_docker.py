"""
Docker build and configuration tests for insights-sdk.

These tests validate that the Docker configuration files are correct
and that the image can be built successfully. They do NOT require
Docker to be running - they test file structure and syntax.

For actual Docker build tests, run:
    docker build -t insights-sdk .
"""

import re
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent


class TestDockerFilesExist:
    """Verify all required Docker files are present."""

    def test_dockerfile_exists(self):
        """Production Dockerfile should exist."""
        dockerfile = PROJECT_ROOT / "Dockerfile"
        assert dockerfile.exists(), "Dockerfile not found"

    def test_dockerfile_dev_exists(self):
        """Development Dockerfile should exist."""
        dockerfile_dev = PROJECT_ROOT / "Dockerfile.dev"
        assert dockerfile_dev.exists(), "Dockerfile.dev not found"

    def test_docker_compose_exists(self):
        """Docker Compose file should exist."""
        compose = PROJECT_ROOT / "docker-compose.yml"
        assert compose.exists(), "docker-compose.yml not found"

    def test_dockerignore_exists(self):
        """Dockerignore file should exist at project root."""
        dockerignore = PROJECT_ROOT / ".dockerignore"
        assert dockerignore.exists(), ".dockerignore not found"


class TestDockerfileBestPractices:
    """Verify Dockerfile follows best practices."""

    @pytest.fixture
    def dockerfile_content(self) -> str:
        """Read production Dockerfile content."""
        return (PROJECT_ROOT / "Dockerfile").read_text()

    @pytest.fixture
    def dockerfile_dev_content(self) -> str:
        """Read development Dockerfile content."""
        return (PROJECT_ROOT / "Dockerfile.dev").read_text()

    def test_uses_slim_base_image(self, dockerfile_content: str):
        """Should use slim base image for smaller size."""
        assert "python:3.12-slim" in dockerfile_content or \
               "python:3.11-slim" in dockerfile_content, \
               "Dockerfile should use a slim Python base image"

    def test_uses_multi_stage_build(self, dockerfile_content: str):
        """Should use multi-stage build for smaller final image."""
        from_count = len(re.findall(r'^FROM\s+', dockerfile_content, re.MULTILINE))
        assert from_count >= 2, "Dockerfile should use multi-stage build (2+ FROM statements)"

    def test_has_non_root_user(self, dockerfile_content: str):
        """Should create and use non-root user for security."""
        assert "useradd" in dockerfile_content or "adduser" in dockerfile_content, \
            "Dockerfile should create a non-root user"
        assert re.search(r'USER\s+\w+', dockerfile_content), \
            "Dockerfile should switch to non-root user"

    def test_sets_pythondontwritebytecode(self, dockerfile_content: str):
        """Should prevent Python from writing bytecode."""
        assert "PYTHONDONTWRITEBYTECODE=1" in dockerfile_content, \
            "Should set PYTHONDONTWRITEBYTECODE=1"

    def test_sets_pythonunbuffered(self, dockerfile_content: str):
        """Should disable Python output buffering."""
        assert "PYTHONUNBUFFERED=1" in dockerfile_content, \
            "Should set PYTHONUNBUFFERED=1"

    def test_uses_buildkit_cache(self, dockerfile_content: str):
        """Should use BuildKit cache mounts for faster builds."""
        assert "--mount=type=cache" in dockerfile_content, \
            "Should use BuildKit cache mounts for pip"

    def test_has_healthcheck(self, dockerfile_content: str):
        """Should include health check for container orchestration."""
        assert "HEALTHCHECK" in dockerfile_content, \
            "Dockerfile should include HEALTHCHECK instruction"

    def test_has_labels(self, dockerfile_content: str):
        """Should include OCI labels for image metadata."""
        assert "LABEL" in dockerfile_content, \
            "Dockerfile should include LABEL instructions"
        assert "org.opencontainers.image" in dockerfile_content, \
            "Should use OCI standard label format"

    def test_cleans_apt_cache(self, dockerfile_content: str):
        """Should clean apt cache to reduce image size."""
        assert "rm -rf /var/lib/apt/lists/*" in dockerfile_content, \
            "Should clean apt cache after installing packages"

    def test_uses_virtual_environment(self, dockerfile_content: str):
        """Should use virtual environment for clean dependency management."""
        assert "venv" in dockerfile_content.lower(), \
            "Should use Python virtual environment"

    def test_dev_dockerfile_has_test_deps(self, dockerfile_dev_content: str):
        """Development Dockerfile should install test dependencies."""
        assert "[dev]" in dockerfile_dev_content, \
            "Dev Dockerfile should install dev dependencies"


class TestDockerCompose:
    """Verify Docker Compose configuration."""

    @pytest.fixture
    def compose_content(self) -> str:
        """Read docker-compose.yml content."""
        return (PROJECT_ROOT / "docker-compose.yml").read_text()

    def test_defines_insights_service(self, compose_content: str):
        """Should define main insights service."""
        assert "insights:" in compose_content, \
            "docker-compose.yml should define 'insights' service"

    def test_defines_test_service(self, compose_content: str):
        """Should define test service."""
        assert "test:" in compose_content, \
            "docker-compose.yml should define 'test' service"

    def test_uses_environment_variables(self, compose_content: str):
        """Should pass credentials via environment variables."""
        assert "SCM_CLIENT_ID" in compose_content, \
            "Should pass SCM_CLIENT_ID environment variable"
        assert "SCM_CLIENT_SECRET" in compose_content, \
            "Should pass SCM_CLIENT_SECRET environment variable"
        assert "SCM_TSG_ID" in compose_content, \
            "Should pass SCM_TSG_ID environment variable"

    def test_has_security_constraints(self, compose_content: str):
        """Should include security constraints."""
        assert "read_only: true" in compose_content, \
            "Should use read-only filesystem"
        assert "cap_drop:" in compose_content, \
            "Should drop capabilities"
        assert "no-new-privileges" in compose_content, \
            "Should prevent privilege escalation"


class TestDockerignore:
    """Verify .dockerignore excludes sensitive and unnecessary files."""

    @pytest.fixture
    def dockerignore_content(self) -> str:
        """Read .dockerignore content."""
        return (PROJECT_ROOT / ".dockerignore").read_text()

    def test_excludes_git(self, dockerignore_content: str):
        """Should exclude .git directory."""
        assert ".git" in dockerignore_content, \
            "Should exclude .git directory"

    def test_excludes_pycache(self, dockerignore_content: str):
        """Should exclude Python cache."""
        assert "__pycache__" in dockerignore_content, \
            "Should exclude __pycache__"

    def test_excludes_venv(self, dockerignore_content: str):
        """Should exclude virtual environments."""
        assert ".venv" in dockerignore_content or "venv" in dockerignore_content, \
            "Should exclude virtual environments"

    def test_excludes_env_files(self, dockerignore_content: str):
        """Should exclude environment files with secrets."""
        assert ".env" in dockerignore_content, \
            "Should exclude .env files"

    def test_excludes_ide_files(self, dockerignore_content: str):
        """Should exclude IDE configuration files."""
        assert ".idea" in dockerignore_content or ".vscode" in dockerignore_content, \
            "Should exclude IDE files"

    def test_excludes_test_cache(self, dockerignore_content: str):
        """Should exclude pytest cache."""
        assert ".pytest_cache" in dockerignore_content, \
            "Should exclude pytest cache"

    def test_excludes_secrets(self, dockerignore_content: str):
        """Should exclude potential secret files."""
        assert "*.pem" in dockerignore_content or "*.key" in dockerignore_content, \
            "Should exclude key/certificate files"


def docker_available() -> bool:
    """Check if Docker is available for integration tests."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.mark.skipif(not docker_available(), reason="Docker not available")
class TestDockerBuildIntegration:
    """
    Integration tests that actually build Docker images.
    Requires Docker to be installed and running.
    """

    @pytest.mark.slow
    def test_production_image_builds(self):
        """Production image should build successfully."""
        import subprocess
        result = subprocess.run(
            ["docker", "build", "-t", "insights-sdk:test", "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    @pytest.mark.slow
    def test_dev_image_builds(self):
        """Development image should build successfully."""
        import subprocess
        result = subprocess.run(
            ["docker", "build", "-f", "Dockerfile.dev", "-t", "insights-sdk:test-dev", "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    @pytest.mark.slow
    def test_cli_runs_in_container(self):
        """CLI should be accessible in container."""
        import subprocess

        subprocess.run(
            ["docker", "build", "-t", "insights-sdk:test", "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            timeout=300
        )

        result = subprocess.run(
            ["docker", "run", "--rm", "insights-sdk:test", "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Container failed: {result.stderr}"
        assert "insights" in result.stdout.lower() or "usage" in result.stdout.lower(), \
            "Help output should mention the CLI"

    @pytest.mark.slow
    def test_image_size_is_reasonable(self):
        """Built image should be reasonably sized (< 500MB)."""
        import subprocess

        subprocess.run(
            ["docker", "build", "-t", "insights-sdk:test", "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            timeout=300
        )

        result = subprocess.run(
            ["docker", "image", "inspect", "insights-sdk:test", "--format", "{{.Size}}"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            size_bytes = int(result.stdout.strip())
            size_mb = size_bytes / (1024 * 1024)
            assert size_mb < 500, f"Image size {size_mb:.1f}MB exceeds 500MB limit"

    @pytest.mark.slow
    def test_container_runs_as_non_root(self):
        """Container should run as non-root user."""
        import subprocess

        subprocess.run(
            ["docker", "build", "-t", "insights-sdk:test", "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            timeout=300
        )

        result = subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "id", "insights-sdk:test"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            assert "uid=0" not in result.stdout, "Container should not run as root"
