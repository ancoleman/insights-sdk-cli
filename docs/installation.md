# Installation Guide

This guide covers all installation methods for the Prisma Access Insights SDK.

## Requirements

- Python 3.10+ (for pip/source installation)
- Docker 20.10+ (for container installation)

## Installation Methods

### 1. pip (Recommended)

```bash
pip install insights-sdk
```

This installs both the `insights` CLI and the `insights_sdk` Python package.

**Verify installation:**

```bash
insights --version
```

### 2. Docker

For isolated, reproducible environments without Python dependencies:

```bash
# Build the image
docker build -t insights .

# Run commands
docker run --rm insights --help
docker run --rm \
    -e SCM_CLIENT_ID \
    -e SCM_CLIENT_SECRET \
    -e SCM_TSG_ID \
    insights users list agent
```

**Using Make:**

```bash
make build                        # Build image
make run ARGS='--help'            # Run with args
make run ARGS='users list agent'  # Query users
```

### 3. From Source

For development or to get the latest unreleased changes:

```bash
git clone https://github.com/paloaltonetworks/insights-sdk.git
cd insights-sdk

# Production install
pip install .

# Development install (includes test dependencies)
make dev
# or: pip install -e ".[dev]"
```

### 4. pip from GitHub

Install a specific version without cloning:

```bash
# Latest main branch
pip install git+https://github.com/paloaltonetworks/insights-sdk.git

# Specific tag/release
pip install git+https://github.com/paloaltonetworks/insights-sdk.git@v0.1.0
```

## CI/CD Integration

### GitHub Actions

```yaml
jobs:
  query:
    runs-on: ubuntu-latest
    steps:
      - name: Install CLI
        run: pip install insights-sdk

      - name: Query users
        env:
          SCM_CLIENT_ID: ${{ secrets.SCM_CLIENT_ID }}
          SCM_CLIENT_SECRET: ${{ secrets.SCM_CLIENT_SECRET }}
          SCM_TSG_ID: ${{ secrets.SCM_TSG_ID }}
        run: insights users count agent
```

### GitLab CI

```yaml
query:
  image: python:3.12-slim
  script:
    - pip install insights-sdk
    - insights users count agent
```

### Requirements.txt

```
# requirements.txt
insights-sdk>=0.1.0
```

## Configuration

### Environment Variables

| Variable | Alternative | Description |
|----------|-------------|-------------|
| `SCM_CLIENT_ID` | `INSIGHTS_CLIENT_ID` | Service account email |
| `SCM_CLIENT_SECRET` | `INSIGHTS_CLIENT_SECRET` | Service account secret |
| `SCM_TSG_ID` | `INSIGHTS_TSG_ID` | Tenant Service Group ID |
| `INSIGHTS_REGION` | - | API region (default: `americas`) |

**Supported regions:** `americas`, `europe`, `asia`, `apac`

### Using .env Files

For local development, create a `.env` file:

```bash
# .env
SCM_CLIENT_ID=your-sa@tsg.iam.panserviceaccount.com
SCM_CLIENT_SECRET=your-secret
SCM_TSG_ID=1234567890
INSIGHTS_REGION=americas
```

The CLI automatically loads `.env` files. For Docker:

```bash
docker run --rm --env-file .env insights users list agent
```

## Comparison

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **pip** | General use | Simple, fast | Requires Python 3.10+ |
| **Docker** | CI/CD, isolation | No Python needed | Larger footprint (~150MB) |
| **Source** | Development | Editable, full control | Requires clone |

## Troubleshooting

### Python version errors

```
ERROR: Package requires Python >=3.10
```

**Fix:** Use Python 3.10+ or use Docker instead.

### Permission denied (Docker)

```
permission denied while trying to connect to the Docker daemon
```

**Fix:** Add your user to the docker group or use `sudo`.

### Module not found

```
ModuleNotFoundError: No module named 'insights_sdk'
```

**Fix:** Ensure you installed the package:

```bash
pip install insights-sdk
# or for development:
pip install -e .
```

### Docker build fails with cache errors

```bash
# Clear BuildKit cache
docker builder prune -f

# Rebuild without cache
docker build --no-cache -t insights .
```
