# Prisma Access Insights SDK

Python SDK and CLI for querying the Palo Alto Networks Prisma Access Insights 3.0 API.

Query users, applications, sites, and security events from your Prisma Access deployment for reporting, monitoring, and analytics.

## Installation

```bash
pip install insights-sdk
```

Or install from source:

```bash
git clone https://github.com/paloaltonetworks/insights-sdk.git
cd insights-sdk
pip install -e .
```

## Quick Start

### 1. Set Credentials

Create a `.env` file or export environment variables:

```bash
# .env
SCM_CLIENT_ID=your-service-account@tsg.iam.panserviceaccount.com
SCM_CLIENT_SECRET=your-secret
SCM_TSG_ID=your-tsg-id
```

### 2. CLI Usage

```bash
# Test connection
insights test

# List agent users from last 24 hours
insights users list agent

# Get connected user count
insights users count agent

# List applications
insights apps list

# Get site traffic
insights sites traffic

# View all commands
insights --help
```

### 3. Python SDK Usage

```python
from insights_sdk import InsightsClient

with InsightsClient(
    client_id="your-client-id",
    client_secret="your-secret",
    tsg_id="your-tsg-id",
) as client:
    # Query users
    users = client.get_agent_users(hours=24)
    print(f"Found {len(users.get('data', []))} users")

    # Query applications
    apps = client.get_applications(hours=24)
```

## Documentation

- **[CLI Reference](docs/cli-reference.md)** - Complete CLI command reference with examples
- **[SDK Guide](docs/sdk-guide.md)** - Python SDK usage, filtering, async support, and best practices

## Command Groups

| Group | Description |
|-------|-------------|
| `insights users` | User queries (list, count, sessions, devices) |
| `insights apps` | Application queries |
| `insights accelerated` | Accelerated app metrics |
| `insights sites` | Site queries |
| `insights security` | PAB security events |
| `insights monitoring` | Monitored user metrics |

## Key Features

- **84+ API endpoints** covered through CLI and SDK
- **Sync and async** Python clients
- **Flexible filtering** with 15+ operators
- **Multiple regions** (Americas, Europe, Asia, APAC)
- **Auto token refresh** - handles OAuth2 automatically

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format and lint
black src/ && ruff check src/
```

## License

MIT
