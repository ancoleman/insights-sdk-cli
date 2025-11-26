"""
Shared pytest fixtures for insights-sdk tests.

Provides mock HTTP responses, sample data, and pre-configured clients
for testing the SDK without making actual API calls.
"""

import pytest
import httpx
import respx
from typing import Any

from insights_sdk import InsightsClient, AsyncInsightsClient
from insights_sdk.models import Region, Operator, FilterRule


# ═══════════════════════════════════════════════════════════════════
# Test Constants
# ═══════════════════════════════════════════════════════════════════

TEST_CLIENT_ID = "test-account@tsg.iam.panserviceaccount.com"
TEST_CLIENT_SECRET = "test-secret-key"
TEST_TSG_ID = "1234567890"
TEST_AUTH_URL = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
TEST_BASE_URL = "https://api.strata.paloaltonetworks.com"
TEST_ACCESS_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test-token"


# ═══════════════════════════════════════════════════════════════════
# Sample Response Data
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_auth_response() -> dict[str, Any]:
    """Sample OAuth2 token response."""
    return {
        "access_token": TEST_ACCESS_TOKEN,
        "token_type": "Bearer",
        "expires_in": 900,
        "scope": f"tsg_id:{TEST_TSG_ID}",
    }


@pytest.fixture
def sample_user_list_response() -> dict[str, Any]:
    """Sample user list API response."""
    return {
        "header": {
            "createdAt": "2025-11-26T15:37:46Z",
            "dataCount": 2,
            "requestId": "test-request-id-123",
            "status": {"subCode": 200},
            "name": "users/agent/user_list",
        },
        "data": [
            {
                "username": "john.doe@example.com",
                "device_name": "LAPTOP-001",
                "platform_type": "prisma_access",
                "agent_version": "6.2.0",
                "client_os_version": "Windows 11",
                "source_city": "San Francisco",
                "source_country": "US",
                "event_time": "2025-11-26T14:30:00Z",
            },
            {
                "username": "jane.smith@example.com",
                "device_name": "MACBOOK-002",
                "platform_type": "prisma_access",
                "agent_version": "6.2.0",
                "client_os_version": "macOS 14.1",
                "source_city": "New York",
                "source_country": "US",
                "event_time": "2025-11-26T14:25:00Z",
            },
        ],
    }


@pytest.fixture
def sample_user_count_response() -> dict[str, Any]:
    """Sample connected user count response."""
    return {
        "header": {
            "createdAt": "2025-11-26T15:37:46Z",
            "dataCount": 1,
            "requestId": "test-request-id-456",
            "status": {"subCode": 200},
            "name": "users/agent/connected_user_count",
        },
        "data": [{"user_count": 42}],
    }


@pytest.fixture
def sample_application_list_response() -> dict[str, Any]:
    """Sample application list response."""
    return {
        "header": {
            "createdAt": "2025-11-26T15:37:46Z",
            "dataCount": 2,
            "requestId": "test-request-id-789",
            "status": {"subCode": 200},
            "name": "applications/internal/application_list",
        },
        "data": [
            {
                "app_name": "Salesforce",
                "app_category": "business-systems",
                "risk_score": 2,
                "bytes_sent": 1024000,
                "bytes_received": 2048000,
                "sessions": 150,
            },
            {
                "app_name": "Slack",
                "app_category": "collaboration",
                "risk_score": 1,
                "bytes_sent": 512000,
                "bytes_received": 1024000,
                "sessions": 300,
            },
        ],
    }


@pytest.fixture
def sample_site_count_response() -> dict[str, Any]:
    """Sample site count response."""
    return {
        "header": {
            "createdAt": "2025-11-26T15:37:46Z",
            "dataCount": 2,
            "requestId": "test-request-id-abc",
            "status": {"subCode": 200},
            "name": "sites/site_count",
        },
        "data": [
            {"node_type": "branch", "site_count": 25},
            {"node_type": "datacenter", "site_count": 5},
        ],
    }


@pytest.fixture
def sample_empty_response() -> dict[str, Any]:
    """Sample response with no data."""
    return {
        "header": {
            "createdAt": "2025-11-26T15:37:46Z",
            "dataCount": 0,
            "requestId": "test-request-id-empty",
            "status": {"subCode": 200},
            "name": "users/agent/user_list",
        },
        "data": [],
    }


@pytest.fixture
def sample_error_response() -> dict[str, Any]:
    """Sample error response."""
    return {
        "error": {
            "code": 400,
            "message": "Invalid request: missing required filter",
        }
    }


# ═══════════════════════════════════════════════════════════════════
# Mock HTTP Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_auth(sample_auth_response):
    """Mock the auth endpoint."""
    with respx.mock:
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        yield


@pytest.fixture
def mock_api(sample_auth_response):
    """Mock both auth and API endpoints for general testing."""
    with respx.mock:
        # Auth endpoint
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        yield respx


# ═══════════════════════════════════════════════════════════════════
# Client Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def client_params() -> dict[str, Any]:
    """Common client parameters."""
    return {
        "client_id": TEST_CLIENT_ID,
        "client_secret": TEST_CLIENT_SECRET,
        "tsg_id": TEST_TSG_ID,
        "region": Region.AMERICAS,
    }


@pytest.fixture
def sync_client(client_params):
    """Create a sync InsightsClient for testing."""
    client = InsightsClient(**client_params)
    yield client
    client.close()


@pytest.fixture
def async_client(client_params):
    """Create an async InsightsClient for testing."""
    return AsyncInsightsClient(**client_params)


# ═══════════════════════════════════════════════════════════════════
# Filter Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_filter_country() -> FilterRule:
    """Sample country filter."""
    return FilterRule(
        property="source_country",
        operator=Operator.IN,
        values=["US", "CA"],
    )


@pytest.fixture
def sample_filter_platform() -> FilterRule:
    """Sample platform filter."""
    return FilterRule(
        property="platform_type",
        operator=Operator.EQUALS,
        values=["prisma_access"],
    )


@pytest.fixture
def sample_filters(sample_filter_country, sample_filter_platform) -> list[FilterRule]:
    """Combined sample filters."""
    return [sample_filter_country, sample_filter_platform]


# ═══════════════════════════════════════════════════════════════════
# Environment Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set mock environment variables."""
    monkeypatch.setenv("SCM_CLIENT_ID", TEST_CLIENT_ID)
    monkeypatch.setenv("SCM_CLIENT_SECRET", TEST_CLIENT_SECRET)
    monkeypatch.setenv("SCM_TSG_ID", TEST_TSG_ID)


@pytest.fixture
def clear_env_vars(monkeypatch):
    """Clear all credential environment variables."""
    for var in [
        "SCM_CLIENT_ID", "SCM_CLIENT_SECRET", "SCM_TSG_ID",
        "INSIGHTS_CLIENT_ID", "INSIGHTS_CLIENT_SECRET", "INSIGHTS_TSG_ID",
    ]:
        monkeypatch.delenv(var, raising=False)
