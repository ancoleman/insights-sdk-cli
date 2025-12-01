# Prisma Access Insights SDK

Python SDK and CLI for querying the Palo Alto Networks Prisma Access Insights 3.0 API.

Query users, applications, sites, and security events from your Prisma Access deployment for reporting, monitoring, and analytics.

## Installation

### pip (recommended)

```bash
pip install insights-sdk
```

### Docker

```bash
docker build -t insights .
docker run --rm insights --help
```

### From source

```bash
git clone https://github.com/ancoleman/insights-sdk.git
cd insights-sdk
make dev
```

See [Installation Guide](docs/installation.md) for all options and CI/CD setup.

## Quick Start

### 1. Set Credentials

```bash
export SCM_CLIENT_ID=your-service-account@tsg.iam.panserviceaccount.com
export SCM_CLIENT_SECRET=your-secret
export SCM_TSG_ID=your-tsg-id
```

### 2. CLI Usage

```bash
insights test                    # Test connection
insights users list agent        # List users (last 24h)
insights users count agent       # Connected user count
insights apps list               # List applications
insights sites traffic           # Site traffic
insights --help                  # All commands
```

### 3. Python SDK

```python
from insights_sdk import InsightsClient

with InsightsClient(
    client_id="your-client-id",
    client_secret="your-secret",
    tsg_id="your-tsg-id",
) as client:
    users = client.get_agent_users(hours=24)
    print(f"Found {len(users.get('data', []))} users")
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Installation](docs/installation.md) | pip, Docker, source, and CI/CD setup |
| [CLI Reference](docs/cli-reference.md) | Complete command reference |
| [SDK Guide](docs/sdk-guide.md) | Python SDK usage and filtering |

## Command Groups

| Group | Description |
|-------|-------------|
| `insights users` | User queries (list, count, sessions, devices) |
| `insights apps` | Application queries |
| `insights sites` | Site queries |
| `insights security` | PAB security events |
| `insights monitoring` | Monitored user metrics |
| `insights accelerated` | Accelerated app metrics |

## Development

```bash
make help       # Show all targets
make dev        # Install with dev deps
make test       # Run tests
make lint       # Run linters
make format     # Format code
make build      # Build Docker image
```

## License

MIT
