# Python SDK Guide

Complete guide for using the Prisma Access Insights Python SDK.

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

```python
from insights_sdk import InsightsClient

# Create client
with InsightsClient(
    client_id="your-service-account@tsg.iam.panserviceaccount.com",
    client_secret="your-secret",
    tsg_id="your-tsg-id",
) as client:
    # Query users from last 24 hours
    users = client.get_agent_users(hours=24)
    print(f"Found {len(users.get('data', []))} users")
```

## Client Configuration

### Basic Configuration

```python
from insights_sdk import InsightsClient, Region

client = InsightsClient(
    client_id="your-client-id",
    client_secret="your-secret",
    tsg_id="your-tsg-id",
    region=Region.AMERICAS,  # Optional, default is AMERICAS
    timeout=30.0,            # Optional, request timeout in seconds
)
```

### Available Regions

```python
from insights_sdk import Region

Region.AMERICAS  # Americas (default)
Region.EUROPE    # Europe
Region.ASIA      # Asia
Region.APAC      # Asia-Pacific
```

### Context Manager (Recommended)

Using context manager ensures proper cleanup:

```python
with InsightsClient(...) as client:
    users = client.get_agent_users(hours=24)
# Connection automatically closed
```

### Manual Close

```python
client = InsightsClient(...)
try:
    users = client.get_agent_users(hours=24)
finally:
    client.close()
```

## Query Methods

### User Queries

```python
# List users by type
users = client.get_agent_users(hours=24)
users = client.get_branch_users(hours=24)
users = client.get_agentless_users(hours=24)
users = client.get_all_users(hours=24)

# User counts
count = client.get_connected_user_count(user_type="agent", hours=24)
count = client.get_connected_user_count(user_type="branch", hours=24)

# Histogram (count over time)
histogram = client.get_user_count_histogram(user_type="agent", hours=24)

# Devices and sessions
devices = client.get_agent_devices(hours=24)
sessions = client.get_agent_sessions(hours=24)

# Risky and monitored users
risky = client.get_risky_user_count(user_type="agent", hours=24)
monitored = client.get_monitored_user_count(hours=24)

# User experience
experience = client.get_user_experience_score(hours=24)
```

### Application Queries

```python
# List applications
apps = client.get_applications(hours=24)

# Application details
info = client.get_app_info(hours=24)

# Grouped queries
by_risk = client.get_apps_by_risk_score(hours=24)
by_tag = client.get_apps_by_tag(hours=24)

# Data transfer
transfer = client.get_app_data_transfer(hours=24)

# Accelerated applications
accelerated = client.get_accelerated_applications(hours=24)
performance = client.get_accelerated_app_performance(hours=24)
```

### Site Queries

```python
# Site information
count = client.get_site_count(hours=24)
traffic = client.get_site_traffic(hours=24)
bandwidth = client.get_site_bandwidth(hours=24)
sessions = client.get_site_session_count(hours=24)

# Search sites
results = client.search_sites(search_term="US West", hours=24)
```

### PAB (Security) Queries

```python
# Access events
access = client.get_pab_access_events(hours=24)
blocked = client.get_pab_access_events_blocked(hours=24)

# Data events
data = client.get_pab_data_events(hours=24)
```

### Export Queries

For large datasets:

```python
# Export (returns download URL or paginated results)
export = client.export_agent_users(hours=24)
export = client.export_branch_users(hours=24)
```

## Filtering

Use filters to narrow query results:

```python
from insights_sdk import FilterRule, Operator

# Create filter rules
filters = [
    FilterRule(
        property="source_country",
        operator=Operator.IN,
        values=["US", "CA"]
    ),
    FilterRule(
        property="platform_type",
        operator=Operator.EQUALS,
        values=["prisma_access"]
    ),
]

# Apply to query
users = client.get_agent_users(hours=24, filters=filters)
```

### Using the Helper Method

```python
# Shorthand for creating filters
users = client.get_agent_users(
    hours=48,
    filters=[
        client.filter("source_country", Operator.IN, ["US", "CA"]),
        client.filter("username", Operator.CONTAINS, ["admin"]),
    ]
)
```

### Available Operators

```python
from insights_sdk import Operator

# List membership
Operator.IN              # value in list
Operator.NOT_IN          # value not in list

# Exact match
Operator.EQUALS          # equals value
Operator.NOT_EQUALS      # not equals value

# Comparisons
Operator.GREATER_THAN
Operator.LESS_THAN
Operator.GREATER_THAN_OR_EQUALS
Operator.LESS_THAN_OR_EQUALS

# String matching
Operator.CONTAINS
Operator.NOT_CONTAINS
Operator.STARTS_WITH
Operator.ENDS_WITH

# Time ranges (usually handled automatically)
Operator.LAST_N_HOURS
Operator.LAST_N_DAYS
Operator.BETWEEN
```

## Response Format

All responses follow this structure:

```python
{
    "header": {
        "createdAt": "2025-11-26T15:37:46Z",
        "dataCount": 42,
        "requestId": "uuid-string",
        "status": {"subCode": 200},
        "name": "users/agent/user_list"
    },
    "data": [
        # List of result objects
    ]
}
```

### Accessing Data

```python
result = client.get_agent_users(hours=24)

# Get data list
data = result.get("data", [])

# Get count from header
count = result.get("header", {}).get("dataCount", 0)

# Iterate results
for user in data:
    print(user.get("username"))
```

## Async Client

For high-performance async applications:

```python
import asyncio
from insights_sdk import AsyncInsightsClient

async def main():
    async with AsyncInsightsClient(
        client_id="...",
        client_secret="...",
        tsg_id="...",
    ) as client:
        # Concurrent queries
        users, apps = await asyncio.gather(
            client.get_agent_users(hours=24),
            client.get_applications(hours=24),
        )

        print(f"Users: {len(users.get('data', []))}")
        print(f"Apps: {len(apps.get('data', []))}")

asyncio.run(main())
```

### Available Async Methods

The async client mirrors the sync client:

```python
await client.get_agent_users(hours=24)
await client.get_all_users(hours=24)
await client.get_connected_user_count(user_type="agent", hours=24)
await client.get_applications(hours=24)
await client.get_site_count(hours=24)
```

## Raw Queries

For endpoints not covered by convenience methods:

```python
# Build query body
body = client._build_query_body(hours=24, filters=None)

# Execute against any endpoint
result = client._post("query/some/custom/endpoint", body)
```

## Error Handling

```python
import httpx

try:
    users = client.get_agent_users(hours=24)
except httpx.HTTPStatusError as e:
    print(f"HTTP error: {e.response.status_code}")
    print(f"Response: {e.response.text}")
except httpx.RequestError as e:
    print(f"Request failed: {e}")
```

## Authentication

The SDK handles authentication automatically:

1. Obtains OAuth2 access token on first request
2. Caches token until near expiry (60-second buffer)
3. Automatically refreshes expired tokens

No manual token management required.

## Best Practices

### 1. Use Context Managers

```python
# Good
with InsightsClient(...) as client:
    data = client.get_agent_users(hours=24)

# Avoid
client = InsightsClient(...)
data = client.get_agent_users(hours=24)
# Forgot to close!
```

### 2. Handle Empty Results

```python
result = client.get_agent_users(hours=24)
data = result.get("data", [])

if not data:
    print("No users found")
else:
    for user in data:
        process(user)
```

### 3. Use Appropriate Time Ranges

```python
# Recent data (last 24 hours)
recent = client.get_agent_users(hours=24)

# Weekly report (last 7 days)
weekly = client.get_agent_users(hours=168)

# Don't query too far back - may timeout or hit limits
```

### 4. Filter Server-Side When Possible

```python
# Good - filter on server
users = client.get_agent_users(
    hours=24,
    filters=[client.filter("source_country", Operator.IN, ["US"])]
)

# Less efficient - filter client-side
users = client.get_agent_users(hours=24)
us_users = [u for u in users.get("data", []) if u.get("source_country") == "US"]
```

### 5. Use Async for Concurrent Queries

```python
# Good - concurrent queries
async with AsyncInsightsClient(...) as client:
    users, apps, sites = await asyncio.gather(
        client.get_agent_users(hours=24),
        client.get_applications(hours=24),
        client.get_site_count(hours=24),
    )

# Slower - sequential queries
with InsightsClient(...) as client:
    users = client.get_agent_users(hours=24)
    apps = client.get_applications(hours=24)
    sites = client.get_site_count(hours=24)
```
