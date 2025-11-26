"""
Unit tests for insights_sdk.client module.

Tests InsightsClient and AsyncInsightsClient API methods.
"""

import pytest
import httpx
import respx

from insights_sdk import InsightsClient, AsyncInsightsClient
from insights_sdk.models import Region, Operator, FilterRule

from .conftest import (
    TEST_CLIENT_ID,
    TEST_CLIENT_SECRET,
    TEST_TSG_ID,
    TEST_AUTH_URL,
    TEST_BASE_URL,
    TEST_ACCESS_TOKEN,
)


class TestInsightsClientInit:
    """Tests for InsightsClient initialization."""

    def test_init_with_defaults(self):
        """Test client initialization with default values."""
        client = InsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        assert client.region == Region.AMERICAS
        # Timeout is now an httpx.Timeout object with specific values
        assert client.timeout.connect == 10.0
        assert client.timeout.read == 30.0
        assert client.base_url == TEST_BASE_URL
        client.close()

    def test_init_with_custom_region(self):
        """Test client initialization with custom region."""
        client = InsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            region=Region.EUROPE,
        )
        assert client.region == Region.EUROPE
        client.close()

    def test_init_with_custom_base_url(self):
        """Test client initialization with custom base URL."""
        custom_url = "https://custom.api.example.com"
        client = InsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            base_url=custom_url,
        )
        assert client.base_url == custom_url
        client.close()

    def test_init_strips_trailing_slash(self):
        """Test that base URL trailing slash is stripped."""
        client = InsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            base_url="https://api.example.com/",
        )
        assert client.base_url == "https://api.example.com"
        client.close()


class TestInsightsClientContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_enter_exit(self):
        """Test using client as context manager."""
        with InsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        ) as client:
            assert isinstance(client, InsightsClient)
        # Client should be closed after exiting context
        assert client._client is None


class TestInsightsClientBuildUrl:
    """Tests for URL building."""

    def test_build_url(self, sync_client):
        """Test URL building for endpoints."""
        url = sync_client._build_url("query/users/agent/user_list")
        expected = f"{TEST_BASE_URL}/insights/v3.0/resource/query/users/agent/user_list"
        assert url == expected

    def test_build_url_different_endpoints(self, sync_client):
        """Test URL building for various endpoints."""
        endpoints = [
            "query/applications/internal/application_list",
            "query/sites/site_count",
            "export/query/users/agent/user_list",
        ]
        for endpoint in endpoints:
            url = sync_client._build_url(endpoint)
            assert endpoint in url
            assert "/insights/v3.0/resource/" in url


class TestInsightsClientBuildQueryBody:
    """Tests for query body building."""

    def test_build_query_body_basic(self, sync_client):
        """Test building basic query body."""
        body = sync_client._build_query_body(hours=24, filters=None)

        assert "filter" in body
        assert "rules" in body["filter"]
        assert len(body["filter"]["rules"]) == 1

        time_rule = body["filter"]["rules"][0]
        assert time_rule["property"] == "event_time"
        assert time_rule["operator"] == "last_n_hours"
        assert time_rule["values"] == [24]

    def test_build_query_body_custom_hours(self, sync_client):
        """Test building query body with custom hours."""
        body = sync_client._build_query_body(hours=168, filters=None)
        assert body["filter"]["rules"][0]["values"] == [168]

    def test_build_query_body_with_filters(self, sync_client, sample_filters):
        """Test building query body with additional filters."""
        body = sync_client._build_query_body(hours=24, filters=sample_filters)

        assert len(body["filter"]["rules"]) == 3  # time + 2 custom
        assert body["filter"]["rules"][1]["property"] == "source_country"
        assert body["filter"]["rules"][2]["property"] == "platform_type"

    def test_build_query_body_filter_operator_serialization(self, sync_client):
        """Test that filter operators are serialized correctly."""
        filters = [
            FilterRule(property="username", operator=Operator.CONTAINS, values=["admin"]),
        ]
        body = sync_client._build_query_body(hours=24, filters=filters)

        username_rule = body["filter"]["rules"][1]
        assert username_rule["operator"] == "contains"  # Should be string, not enum


class TestInsightsClientFilterHelper:
    """Tests for the filter() helper method."""

    def test_filter_creates_filter_rule(self, sync_client):
        """Test that filter() creates a FilterRule."""
        rule = sync_client.filter("username", Operator.IN, ["john.doe"])

        assert isinstance(rule, FilterRule)
        assert rule.property == "username"
        assert rule.operator == Operator.IN
        assert rule.values == ["john.doe"]

    def test_filter_with_multiple_values(self, sync_client):
        """Test filter() with multiple values."""
        rule = sync_client.filter("source_country", Operator.IN, ["US", "CA", "MX"])
        assert rule.values == ["US", "CA", "MX"]


class TestInsightsClientUserQueries:
    """Tests for user query methods."""

    @respx.mock
    def test_get_agent_users(self, sync_client, sample_auth_response, sample_user_list_response):
        """Test get_agent_users method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        result = sync_client.get_agent_users(hours=24)

        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["username"] == "john.doe@example.com"

    @respx.mock
    def test_get_branch_users(self, sync_client, sample_auth_response, sample_user_list_response):
        """Test get_branch_users method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/branch/user_list").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        result = sync_client.get_branch_users(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_agentless_users(self, sync_client, sample_auth_response, sample_user_list_response):
        """Test get_agentless_users method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agentless/users").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        result = sync_client.get_agentless_users(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_all_users(self, sync_client, sample_auth_response, sample_user_list_response):
        """Test get_all_users method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/all/user_list_all").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        result = sync_client.get_all_users(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_connected_user_count(self, sync_client, sample_auth_response, sample_user_count_response):
        """Test get_connected_user_count method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/connected_user_count").mock(
            return_value=httpx.Response(200, json=sample_user_count_response)
        )

        result = sync_client.get_connected_user_count(user_type="agent", hours=24)

        assert "data" in result
        assert result["data"][0]["user_count"] == 42

    @respx.mock
    def test_get_user_count_histogram(self, sync_client, sample_auth_response):
        """Test get_user_count_histogram method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/user_count_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01", "count": 10}]})
        )

        result = sync_client.get_user_count_histogram(user_type="agent", hours=24)
        assert "data" in result

    @respx.mock
    def test_get_agent_devices(self, sync_client, sample_auth_response):
        """Test get_agent_devices method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/device_list").mock(
            return_value=httpx.Response(200, json={"data": [{"device_name": "LAPTOP-001"}]})
        )

        result = sync_client.get_agent_devices(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_agent_sessions(self, sync_client, sample_auth_response):
        """Test get_agent_sessions method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/other/session_list").mock(
            return_value=httpx.Response(200, json={"data": [{"session_id": "123"}]})
        )

        result = sync_client.get_agent_sessions(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_risky_user_count(self, sync_client, sample_auth_response):
        """Test get_risky_user_count method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/agent/risky_user_count").mock(
            return_value=httpx.Response(200, json={"data": [{"count": 5}]})
        )

        result = sync_client.get_risky_user_count(user_type="agent", hours=24)
        assert "data" in result

    @respx.mock
    def test_get_monitored_user_count(self, sync_client, sample_auth_response):
        """Test get_monitored_user_count method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/user/monitored/user_count").mock(
            return_value=httpx.Response(200, json={"data": [{"count": 100}]})
        )

        result = sync_client.get_monitored_user_count(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_user_experience_score(self, sync_client, sample_auth_response):
        """Test get_user_experience_score method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/monitored/user_experience_score").mock(
            return_value=httpx.Response(200, json={"data": [{"score": 85}]})
        )

        result = sync_client.get_user_experience_score(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_agent_users_with_filters(
        self, sync_client, sample_auth_response, sample_user_list_response, sample_filters
    ):
        """Test get_agent_users with custom filters."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        route = respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        result = sync_client.get_agent_users(hours=48, filters=sample_filters)

        assert "data" in result
        # Verify the request body contained the filters
        request = route.calls[0].request
        import json
        body = json.loads(request.content)
        assert len(body["filter"]["rules"]) == 3  # time + 2 custom filters


class TestInsightsClientApplicationQueries:
    """Tests for application query methods."""

    @respx.mock
    def test_get_applications(self, sync_client, sample_auth_response, sample_application_list_response):
        """Test get_applications method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/application_list").mock(
            return_value=httpx.Response(200, json=sample_application_list_response)
        )

        result = sync_client.get_applications(hours=24)

        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["app_name"] == "Salesforce"

    @respx.mock
    def test_get_app_info(self, sync_client, sample_auth_response):
        """Test get_app_info method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/app_info").mock(
            return_value=httpx.Response(200, json={"data": [{"app_name": "TestApp"}]})
        )

        result = sync_client.get_app_info(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_apps_by_risk_score(self, sync_client, sample_auth_response):
        """Test get_apps_by_risk_score method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/app_by_risk_score").mock(
            return_value=httpx.Response(200, json={"data": [{"risk_score": 5, "count": 10}]})
        )

        result = sync_client.get_apps_by_risk_score(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_apps_by_tag(self, sync_client, sample_auth_response):
        """Test get_apps_by_tag method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/app_by_tag").mock(
            return_value=httpx.Response(200, json={"data": [{"tag": "business", "count": 20}]})
        )

        result = sync_client.get_apps_by_tag(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_app_data_transfer(self, sync_client, sample_auth_response):
        """Test get_app_data_transfer method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/total_data_transfer_application").mock(
            return_value=httpx.Response(200, json={"data": [{"bytes_sent": 1024}]})
        )

        result = sync_client.get_app_data_transfer(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_accelerated_applications(self, sync_client, sample_auth_response):
        """Test get_accelerated_applications method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/accelerated_application_list").mock(
            return_value=httpx.Response(200, json={"data": [{"app_name": "AccelApp"}]})
        )

        result = sync_client.get_accelerated_applications(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_accelerated_app_performance(self, sync_client, sample_auth_response):
        """Test get_accelerated_app_performance method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/performance_boost").mock(
            return_value=httpx.Response(200, json={"data": [{"boost_percent": 25}]})
        )

        result = sync_client.get_accelerated_app_performance(hours=24)
        assert "data" in result


class TestInsightsClientSiteQueries:
    """Tests for site query methods."""

    @respx.mock
    def test_get_site_count(self, sync_client, sample_auth_response, sample_site_count_response):
        """Test get_site_count method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/site_count").mock(
            return_value=httpx.Response(200, json=sample_site_count_response)
        )

        result = sync_client.get_site_count(hours=24)

        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["site_count"] == 25

    @respx.mock
    def test_get_site_traffic(self, sync_client, sample_auth_response):
        """Test get_site_traffic method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/site_traffic").mock(
            return_value=httpx.Response(200, json={"data": [{"site_name": "HQ", "traffic": 1000}]})
        )

        result = sync_client.get_site_traffic(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_site_bandwidth(self, sync_client, sample_auth_response):
        """Test get_site_bandwidth method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/bandwidth_consumption_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01", "bandwidth": 500}]})
        )

        result = sync_client.get_site_bandwidth(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_site_session_count(self, sync_client, sample_auth_response):
        """Test get_site_session_count method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/session_count").mock(
            return_value=httpx.Response(200, json={"data": [{"session_count": 150}]})
        )

        result = sync_client.get_site_session_count(hours=24)
        assert "data" in result

    @respx.mock
    def test_search_sites(self, sync_client, sample_auth_response):
        """Test search_sites method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        route = respx.post(url__regex=r".*/query/sites/site_location_search_contains").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        result = sync_client.search_sites(search_term="US West", hours=24)

        assert "data" in result
        # Verify search term was included in body
        import json
        body = json.loads(route.calls[0].request.content)
        assert body["search"] == "US West"


class TestInsightsClientPABQueries:
    """Tests for PAB (Private Access Browser) query methods."""

    @respx.mock
    def test_get_pab_access_events(self, sync_client, sample_auth_response):
        """Test get_pab_access_events method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/pab/access_events").mock(
            return_value=httpx.Response(200, json={"data": [{"event_id": "1"}]})
        )

        result = sync_client.get_pab_access_events(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_pab_access_events_blocked(self, sync_client, sample_auth_response):
        """Test get_pab_access_events_blocked method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/access_events_blocked").mock(
            return_value=httpx.Response(200, json={"data": [{"event_id": "2", "blocked": True}]})
        )

        result = sync_client.get_pab_access_events_blocked(hours=24)
        assert "data" in result

    @respx.mock
    def test_get_pab_data_events(self, sync_client, sample_auth_response):
        """Test get_pab_data_events method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/pab/data_events").mock(
            return_value=httpx.Response(200, json={"data": [{"event_id": "3"}]})
        )

        result = sync_client.get_pab_data_events(hours=24)
        assert "data" in result


class TestInsightsClientExportQueries:
    """Tests for export query methods."""

    @respx.mock
    def test_export_agent_users(self, sync_client, sample_auth_response):
        """Test export_agent_users method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/export/query/users/agent/user_list").mock(
            return_value=httpx.Response(200, json={"data": [{"username": "user1"}]})
        )

        result = sync_client.export_agent_users(hours=24)
        assert "data" in result

    @respx.mock
    def test_export_branch_users(self, sync_client, sample_auth_response):
        """Test export_branch_users method."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/export/query/users/branch/user_list").mock(
            return_value=httpx.Response(200, json={"data": [{"username": "branch_user1"}]})
        )

        result = sync_client.export_branch_users(hours=24)
        assert "data" in result


class TestInsightsClientErrorHandling:
    """Tests for error handling."""

    @respx.mock
    def test_http_error_propagated(self, sync_client, sample_auth_response):
        """Test that HTTP errors are propagated."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(400, json={"error": "Bad request"})
        )

        with pytest.raises(httpx.HTTPStatusError):
            sync_client.get_agent_users(hours=24)

    @respx.mock
    def test_auth_error_propagated(self, sync_client):
        """Test that auth errors are propagated."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(401, json={"error": "invalid_client"})
        )

        with pytest.raises(httpx.HTTPStatusError):
            sync_client.get_agent_users(hours=24)


class TestInsightsClientHeaders:
    """Tests for request headers."""

    @respx.mock
    def test_headers_include_region(self, sync_client, sample_auth_response, sample_user_list_response):
        """Test that requests include region header."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        route = respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        sync_client.get_agent_users(hours=24)

        request = route.calls[0].request
        assert request.headers["X-PANW-Region"] == "americas"

    @respx.mock
    def test_headers_include_auth_token(self, sync_client, sample_auth_response, sample_user_list_response):
        """Test that requests include authorization header."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        route = respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        sync_client.get_agent_users(hours=24)

        request = route.calls[0].request
        assert "Bearer" in request.headers["Authorization"]


class TestAsyncInsightsClient:
    """Tests for AsyncInsightsClient."""

    def test_init(self, async_client):
        """Test async client initialization."""
        assert async_client.region == Region.AMERICAS
        # Timeout is now an httpx.Timeout object with specific values
        assert async_client.timeout.connect == 10.0
        assert async_client.timeout.read == 30.0

    @pytest.mark.asyncio
    async def test_context_manager_async(self):
        """Test async context manager."""
        async with AsyncInsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        ) as client:
            assert isinstance(client, AsyncInsightsClient)

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_agent_users_async(self, sample_auth_response, sample_user_list_response):
        """Test async get_agent_users."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        async with AsyncInsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        ) as client:
            result = await client.get_agent_users(hours=24)

        assert "data" in result
        assert len(result["data"]) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_all_users_async(self, sample_auth_response, sample_user_list_response):
        """Test async get_all_users."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/all/user_list_all").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        async with AsyncInsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        ) as client:
            result = await client.get_all_users(hours=24)

        assert "data" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_connected_user_count_async(self, sample_auth_response, sample_user_count_response):
        """Test async get_connected_user_count."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/connected_user_count").mock(
            return_value=httpx.Response(200, json=sample_user_count_response)
        )

        async with AsyncInsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        ) as client:
            result = await client.get_connected_user_count(user_type="agent", hours=24)

        assert "data" in result
        assert result["data"][0]["user_count"] == 42

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_applications_async(self, sample_auth_response, sample_application_list_response):
        """Test async get_applications."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/application_list").mock(
            return_value=httpx.Response(200, json=sample_application_list_response)
        )

        async with AsyncInsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        ) as client:
            result = await client.get_applications(hours=24)

        assert "data" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_site_count_async(self, sample_auth_response, sample_site_count_response):
        """Test async get_site_count."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/site_count").mock(
            return_value=httpx.Response(200, json=sample_site_count_response)
        )

        async with AsyncInsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        ) as client:
            result = await client.get_site_count(hours=24)

        assert "data" in result

    def test_build_query_body_async(self, async_client):
        """Test async client query body building."""
        body = async_client._build_query_body(hours=24, filters=None)
        assert "filter" in body
        assert body["filter"]["rules"][0]["values"] == [24]

    def test_build_query_body_with_filters_async(self, async_client, sample_filters):
        """Test async client query body building with filters."""
        body = async_client._build_query_body(hours=48, filters=sample_filters)
        assert len(body["filter"]["rules"]) == 3

    def test_filter_helper_async(self, async_client):
        """Test async client filter helper."""
        rule = async_client.filter("username", Operator.IN, ["test"])
        assert isinstance(rule, FilterRule)


class TestInsightsClientRetry:
    """Tests for InsightsClient retry logic."""

    def test_init_with_custom_retry_settings(self):
        """Test client initialization with custom retry settings."""
        client = InsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            max_retries=5,
            retry_backoff=2.0,
        )
        assert client.max_retries == 5
        assert client.retry_backoff == 2.0
        client.close()

    @respx.mock
    def test_retry_on_server_error(self, sample_auth_response, sample_user_list_response):
        """Test that API retries on 5xx errors."""
        # Auth always succeeds
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )

        # First call returns 503, second succeeds
        api_route = respx.post(url__regex=r".*/query/users/agent/user_list")
        api_route.side_effect = [
            httpx.Response(503, json={"error": "service_unavailable"}),
            httpx.Response(200, json=sample_user_list_response),
        ]

        with InsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            retry_backoff=0.01,  # Fast retries for testing
        ) as client:
            result = client.get_agent_users()

        assert "data" in result
        assert api_route.call_count == 2

    @respx.mock
    def test_retry_exhausted_raises_error(self, sample_auth_response):
        """Test that API raises after all retries exhausted."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )

        api_route = respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(500, json={"error": "internal_error"})
        )

        with InsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            max_retries=2,
            retry_backoff=0.01,
        ) as client:
            with pytest.raises(httpx.HTTPStatusError):
                client.get_agent_users()

        # Should have tried 3 times (1 + 2 retries)
        assert api_route.call_count == 3

    @respx.mock
    def test_no_retry_on_client_error(self, sample_auth_response):
        """Test that API doesn't retry on 4xx errors (except 429)."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )

        api_route = respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(400, json={"error": "bad_request"})
        )

        with InsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            retry_backoff=0.01,
        ) as client:
            with pytest.raises(httpx.HTTPStatusError):
                client.get_agent_users()

        # Should only try once - 400 is not retryable
        assert api_route.call_count == 1

    @respx.mock
    def test_retry_on_rate_limit(self, sample_auth_response, sample_user_list_response):
        """Test that API retries on 429 rate limit."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )

        api_route = respx.post(url__regex=r".*/query/users/agent/user_list")
        api_route.side_effect = [
            httpx.Response(429, json={"error": "rate_limited"}),
            httpx.Response(200, json=sample_user_list_response),
        ]

        with InsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            retry_backoff=0.01,
        ) as client:
            result = client.get_agent_users()

        assert "data" in result
        assert api_route.call_count == 2


class TestAsyncInsightsClientRetry:
    """Tests for AsyncInsightsClient retry logic."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_retry_on_server_error(self, sample_auth_response, sample_user_list_response):
        """Test that async API retries on 5xx errors."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )

        api_route = respx.post(url__regex=r".*/query/users/agent/user_list")
        api_route.side_effect = [
            httpx.Response(502, json={"error": "bad_gateway"}),
            httpx.Response(200, json=sample_user_list_response),
        ]

        async with AsyncInsightsClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            retry_backoff=0.01,
        ) as client:
            result = await client.get_agent_users()

        assert "data" in result
        assert api_route.call_count == 2
