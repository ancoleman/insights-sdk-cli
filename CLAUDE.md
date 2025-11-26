# CLAUDE.md

Python SDK for Palo Alto Networks Prisma Access Insights 3.0 API.

## Quick Reference

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Test
pytest tests/ -v
pytest tests/test_cli_integration.py -v  # Real API tests (requires credentials)

# CLI
insights test                    # Test connection
insights users list agent        # List users
insights users count agent       # User count
insights apps list               # List apps
insights sites list              # Site count
```

## Project Structure

```
src/insights_sdk/
├── cli.py      # Typer CLI (command groups: users, apps, sites, security, monitoring, accelerated)
├── client.py   # InsightsClient & AsyncInsightsClient
├── auth.py     # OAuth2 with auto token refresh + retry logic
└── models.py   # Pydantic models (FilterRule, Operator, Region)
```

## API Essentials

- **Base URL**: `https://api.strata.paloaltonetworks.com/insights/v3.0/resource/`
- **Auth**: OAuth2 client credentials → Bearer token (15-min expiry, auto-refresh)
- **All endpoints**: POST with filter body, response `data` is always a list

## Adding Features

1. **New SDK method** in `client.py`:
```python
def get_something(self, hours: int = 24, filters: Optional[list[FilterRule]] = None) -> dict:
    body = self._build_query_body(hours, filters)
    return self._post("query/path/to/endpoint", body)
```

2. **New CLI command** in `cli.py` - add to appropriate `*_app` group (users_app, apps_app, etc.)

## IMPORTANT: API Quirks

- **Agent endpoints REQUIRE `platform_type` filter** - CLI adds automatically
- **Histogram endpoints REQUIRE `histogram` config object** - CLI adds automatically
- **`users sessions agent` REQUIRES `username` filter**
- **Region header required**: `X-PANW-Region: americas|europe|asia|apac`

## Known API Limitations

These endpoints return errors (not SDK bugs):
- `accelerated/*` → DATA10003 (invalid resource)
- `monitoring/*` → DATA10003 (invalid resource)
- `security/*` → REST10005 (requires PAB permissions)
- `sites/session_count` → GCP10002 (backend syntax error)
- `sites/site_location_search_contains` → 500 errors

## DO NOT

- DO NOT remove `platform_type` filter from agent endpoints
- DO NOT remove histogram config from `*_histogram` endpoints
- DO NOT expect non-list responses from API (always `{"data": [...]}`)
- DO NOT hardcode credentials - use env vars: `SCM_CLIENT_ID`, `SCM_CLIENT_SECRET`, `SCM_TSG_ID`

## Environment Variables

```bash
export SCM_CLIENT_ID="your-sa@tsg.iam.panserviceaccount.com"
export SCM_CLIENT_SECRET="your-secret"
export SCM_TSG_ID="your-tsg-id"
# Or use INSIGHTS_* prefix
```

## Test Coverage

- 260 unit tests (mocked HTTP)
- 32 integration tests (real API, skipped without credentials)
- Run all: `pytest tests/ -v`
