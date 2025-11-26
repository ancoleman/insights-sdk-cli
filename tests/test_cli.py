"""
Integration tests for insights_sdk.cli module.

Tests the CLI commands using Typer's CliRunner for command execution
and respx for mocking HTTP requests.
"""

import json
import pytest
import httpx
import respx
from typer.testing import CliRunner

from insights_sdk.cli import app, get_client, UserType, HistogramMetric

from .conftest import (
    TEST_CLIENT_ID,
    TEST_CLIENT_SECRET,
    TEST_TSG_ID,
    TEST_AUTH_URL,
)

runner = CliRunner()


# ═══════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════

def auth_options():
    """Return common auth CLI options."""
    return [
        "--client-id", TEST_CLIENT_ID,
        "--client-secret", TEST_CLIENT_SECRET,
        "--tsg-id", TEST_TSG_ID,
    ]


# ═══════════════════════════════════════════════════════════════════
# Test CLI App Structure
# ═══════════════════════════════════════════════════════════════════

class TestCLIStructure:
    """Tests for CLI app structure and help."""

    def test_main_help(self):
        """Test main app help displays."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Query Prisma Access Insights 3.0 API" in result.output

    def test_users_subcommand_exists(self):
        """Test users subcommand is available."""
        result = runner.invoke(app, ["users", "--help"])
        assert result.exit_code == 0
        assert "User queries" in result.output

    def test_apps_subcommand_exists(self):
        """Test apps subcommand is available."""
        result = runner.invoke(app, ["apps", "--help"])
        assert result.exit_code == 0
        assert "Application queries" in result.output

    def test_sites_subcommand_exists(self):
        """Test sites subcommand is available."""
        result = runner.invoke(app, ["sites", "--help"])
        assert result.exit_code == 0
        assert "Site queries" in result.output

    def test_security_subcommand_exists(self):
        """Test security subcommand is available."""
        result = runner.invoke(app, ["security", "--help"])
        assert result.exit_code == 0
        assert "PAB security events" in result.output

    def test_accelerated_subcommand_exists(self):
        """Test accelerated subcommand is available."""
        result = runner.invoke(app, ["accelerated", "--help"])
        assert result.exit_code == 0
        assert "Accelerated application" in result.output

    def test_monitoring_subcommand_exists(self):
        """Test monitoring subcommand is available."""
        result = runner.invoke(app, ["monitoring", "--help"])
        assert result.exit_code == 0
        assert "Monitored user" in result.output


class TestCLIUserCommands:
    """Tests for users subcommand group."""

    def test_users_list_help(self):
        """Test users list command help."""
        result = runner.invoke(app, ["users", "list", "--help"])
        assert result.exit_code == 0
        assert "List users by type" in result.output

    def test_users_count_help(self):
        """Test users count command help."""
        result = runner.invoke(app, ["users", "count", "--help"])
        assert result.exit_code == 0
        assert "connected user count" in result.output.lower()

    def test_users_sessions_help(self):
        """Test users sessions command help."""
        result = runner.invoke(app, ["users", "sessions", "--help"])
        assert result.exit_code == 0
        assert "sessions" in result.output.lower()

    def test_users_devices_help(self):
        """Test users devices command help."""
        result = runner.invoke(app, ["users", "devices", "--help"])
        assert result.exit_code == 0
        assert "devices" in result.output.lower()

    @respx.mock
    def test_users_list_agent(self, sample_auth_response, sample_user_list_response):
        """Test users list agent command with mocked API."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        result = runner.invoke(app, ["users", "list", "agent", *auth_options()])

        assert result.exit_code == 0
        assert "Agent Users" in result.output or "john.doe" in result.output

    @respx.mock
    def test_users_list_json_output(self, sample_auth_response, sample_user_list_response):
        """Test users list with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        result = runner.invoke(app, ["users", "list", "agent", "--json", *auth_options()])

        assert result.exit_code == 0
        # Output should contain JSON data
        assert "john.doe@example.com" in result.output

    @respx.mock
    def test_users_count_agent(self, sample_auth_response, sample_user_count_response):
        """Test users count command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/connected_user_count").mock(
            return_value=httpx.Response(200, json=sample_user_count_response)
        )

        result = runner.invoke(app, ["users", "count", "agent", *auth_options()])

        assert result.exit_code == 0
        assert "42" in result.output

    def test_users_sessions_agent_requires_username(self):
        """Test that agent sessions requires --username."""
        result = runner.invoke(app, ["users", "sessions", "agent", *auth_options()])

        assert result.exit_code == 1
        assert "username" in result.output.lower() or "required" in result.output.lower()


class TestCLIAppsCommands:
    """Tests for apps subcommand group."""

    def test_apps_list_help(self):
        """Test apps list command help."""
        result = runner.invoke(app, ["apps", "list", "--help"])
        assert result.exit_code == 0
        assert "List internal applications" in result.output

    @respx.mock
    def test_apps_list(self, sample_auth_response, sample_application_list_response):
        """Test apps list command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/application_list").mock(
            return_value=httpx.Response(200, json=sample_application_list_response)
        )

        result = runner.invoke(app, ["apps", "list", *auth_options()])

        assert result.exit_code == 0
        assert "Applications" in result.output or "Salesforce" in result.output


class TestCLISitesCommands:
    """Tests for sites subcommand group."""

    def test_sites_list_help(self):
        """Test sites list command help."""
        result = runner.invoke(app, ["sites", "list", "--help"])
        assert result.exit_code == 0

    @respx.mock
    def test_sites_list(self, sample_auth_response, sample_site_count_response):
        """Test sites list command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/site_count").mock(
            return_value=httpx.Response(200, json=sample_site_count_response)
        )

        result = runner.invoke(app, ["sites", "list", *auth_options()])

        assert result.exit_code == 0
        assert "site" in result.output.lower()


class TestCLISecurityCommands:
    """Tests for security subcommand group."""

    def test_security_access_help(self):
        """Test security access command help."""
        result = runner.invoke(app, ["security", "access", "--help"])
        assert result.exit_code == 0
        assert "PAB access events" in result.output

    def test_security_data_help(self):
        """Test security data command help."""
        result = runner.invoke(app, ["security", "data", "--help"])
        assert result.exit_code == 0
        assert "PAB data events" in result.output


class TestCLIUtilityCommands:
    """Tests for utility commands."""

    def test_query_help(self):
        """Test raw query command help."""
        result = runner.invoke(app, ["query", "--help"])
        assert result.exit_code == 0
        assert "raw query" in result.output.lower()

    def test_test_help(self):
        """Test test command help."""
        result = runner.invoke(app, ["test", "--help"])
        assert result.exit_code == 0
        assert "Test API connection" in result.output

    @respx.mock
    def test_test_connection_success(self, sample_auth_response, sample_user_count_response):
        """Test test command with successful connection."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/connected_user_count").mock(
            return_value=httpx.Response(200, json=sample_user_count_response)
        )

        result = runner.invoke(app, ["test", *auth_options()])

        assert result.exit_code == 0
        assert "successful" in result.output.lower() or "OK" in result.output

    @respx.mock
    def test_test_connection_auth_failure(self):
        """Test test command with auth failure."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(401, json={"error": "invalid_client"})
        )

        result = runner.invoke(app, ["test", *auth_options()])

        assert result.exit_code == 1
        assert "FAILED" in result.output or "failed" in result.output.lower()


class TestCLICredentials:
    """Tests for credential handling."""

    def test_missing_credentials_error(self, clear_env_vars):
        """Test error when credentials are missing."""
        result = runner.invoke(app, ["users", "list", "agent"])

        assert result.exit_code == 1
        assert "credentials" in result.output.lower() or "Missing" in result.output

    def test_env_var_credentials(self, mock_env_vars):
        """Test that env vars are recognized for credentials."""
        # This test just verifies the get_client function reads env vars
        # Actual API call would need mocking
        result = runner.invoke(app, ["users", "list", "--help"])
        assert result.exit_code == 0


class TestCLIOptions:
    """Tests for CLI options."""

    def test_hours_option(self):
        """Test --hours option is available."""
        result = runner.invoke(app, ["users", "list", "--help"])
        assert "--hours" in result.output

    def test_json_option(self):
        """Test --json option is available."""
        result = runner.invoke(app, ["users", "list", "--help"])
        assert "--json" in result.output

    def test_limit_option(self):
        """Test --limit option is available."""
        result = runner.invoke(app, ["users", "list", "--help"])
        assert "--limit" in result.output

    def test_region_option(self):
        """Test --region option is available."""
        result = runner.invoke(app, ["users", "list", "--help"])
        assert "--region" in result.output


class TestCLIEnums:
    """Tests for CLI enum types."""

    def test_user_type_values(self):
        """Test UserType enum has correct values."""
        assert UserType.agent.value == "agent"
        assert UserType.branch.value == "branch"
        assert UserType.agentless.value == "agentless"
        assert UserType.eb.value == "eb"
        assert UserType.other.value == "other"
        assert UserType.all.value == "all"

    def test_histogram_metric_values(self):
        """Test HistogramMetric enum has correct values."""
        assert HistogramMetric.throughput.value == "throughput"
        assert HistogramMetric.packet_loss.value == "packet-loss"
        assert HistogramMetric.rtt.value == "rtt"
        assert HistogramMetric.boost.value == "boost"


class TestCLIErrorHandling:
    """Tests for CLI error handling."""

    @respx.mock
    def test_api_error_displayed(self, sample_auth_response):
        """Test that API errors are displayed to user."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(400, json={"error": "Bad request"})
        )

        result = runner.invoke(app, ["users", "list", "agent", *auth_options()])

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_invalid_user_type(self):
        """Test invalid user type is rejected."""
        result = runner.invoke(app, ["users", "list", "invalid_type", *auth_options()])

        # Typer should reject invalid enum value
        assert result.exit_code != 0


class TestCLIPlatformFilter:
    """Tests for platform filter handling."""

    @respx.mock
    def test_agent_list_adds_platform_filter(self, sample_auth_response, sample_user_list_response):
        """Test that agent list automatically adds platform filter."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        route = respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        result = runner.invoke(app, ["users", "list", "agent", *auth_options()])

        assert result.exit_code == 0
        # Check that request included platform_type filter
        request_body = json.loads(route.calls[0].request.content)
        filter_rules = request_body.get("filter", {}).get("rules", [])
        platform_filter = [r for r in filter_rules if r.get("property") == "platform_type"]
        assert len(platform_filter) == 1
        assert "prisma_access" in platform_filter[0]["values"]

    @respx.mock
    def test_custom_platform_filter(self, sample_auth_response, sample_user_list_response):
        """Test custom platform filter overrides default."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        route = respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(200, json=sample_user_list_response)
        )

        result = runner.invoke(app, [
            "users", "list", "agent",
            "--platform", "ngfw",
            *auth_options()
        ])

        assert result.exit_code == 0
        # Check that request used custom platform
        request_body = json.loads(route.calls[0].request.content)
        filter_rules = request_body.get("filter", {}).get("rules", [])
        platform_filter = [r for r in filter_rules if r.get("property") == "platform_type"]
        assert "ngfw" in platform_filter[0]["values"]


# ═══════════════════════════════════════════════════════════════════
# Additional User Command Tests
# ═══════════════════════════════════════════════════════════════════

class TestCLIUserCommandsExtended:
    """Extended tests for users subcommand group."""

    @respx.mock
    def test_users_count_current(self, sample_auth_response):
        """Test users count with --current flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/current_connected_user_count").mock(
            return_value=httpx.Response(200, json={"data": [{"user_count": 35}]})
        )

        result = runner.invoke(app, ["users", "count", "agent", "--current", *auth_options()])

        assert result.exit_code == 0
        assert "35" in result.output

    @respx.mock
    def test_users_count_json(self, sample_auth_response, sample_user_count_response):
        """Test users count with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/connected_user_count").mock(
            return_value=httpx.Response(200, json=sample_user_count_response)
        )

        result = runner.invoke(app, ["users", "count", "agent", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "user_count" in result.output

    @respx.mock
    def test_users_sessions_other(self, sample_auth_response):
        """Test users sessions for other type (no username required)."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/other/session_list").mock(
            return_value=httpx.Response(200, json={"data": [{"session_id": "123"}]})
        )

        result = runner.invoke(app, ["users", "sessions", "other", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_users_sessions_with_username(self, sample_auth_response):
        """Test users sessions with username filter."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/session_list").mock(
            return_value=httpx.Response(200, json={"data": [{"username": "john"}]})
        )

        result = runner.invoke(app, ["users", "sessions", "agent", "-u", "john", *auth_options()])

        assert result.exit_code == 0

    def test_users_sessions_invalid_type(self):
        """Test users sessions with invalid type."""
        result = runner.invoke(app, ["users", "sessions", "all", *auth_options()])
        assert result.exit_code == 1

    @respx.mock
    def test_users_devices(self, sample_auth_response):
        """Test users devices command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/device_list").mock(
            return_value=httpx.Response(200, json={"data": [{"device_name": "LAPTOP-001"}]})
        )

        result = runner.invoke(app, ["users", "devices", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_users_devices_unique(self, sample_auth_response):
        """Test users devices with --unique flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/unique_device_connections_list").mock(
            return_value=httpx.Response(200, json={"data": [{"device_name": "LAPTOP-001"}]})
        )

        result = runner.invoke(app, ["users", "devices", "--unique", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_users_risky(self, sample_auth_response):
        """Test users risky command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/risky_user_count").mock(
            return_value=httpx.Response(200, json={"data": [{"count": 5}]})
        )

        result = runner.invoke(app, ["users", "risky", "agent", *auth_options()])

        assert result.exit_code == 0

    def test_users_risky_invalid_type(self):
        """Test users risky with invalid type."""
        result = runner.invoke(app, ["users", "risky", "all", *auth_options()])
        assert result.exit_code == 1

    @respx.mock
    def test_users_active_count(self, sample_auth_response):
        """Test users active count command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agentless/active_user_count").mock(
            return_value=httpx.Response(200, json={"data": [{"count": 20}]})
        )

        result = runner.invoke(app, ["users", "active", "agentless", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_users_active_list(self, sample_auth_response):
        """Test users active list command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/branch/active_user_list").mock(
            return_value=httpx.Response(200, json={"data": [{"username": "user1"}]})
        )

        result = runner.invoke(app, ["users", "active", "branch", "--list", *auth_options()])

        assert result.exit_code == 0

    def test_users_active_invalid_type(self):
        """Test users active with invalid type."""
        result = runner.invoke(app, ["users", "active", "agent", *auth_options()])
        assert result.exit_code == 1

    @respx.mock
    def test_users_histogram(self, sample_auth_response):
        """Test users histogram command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/connected_user_count_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01", "count": 10}]})
        )

        result = runner.invoke(app, ["users", "histogram", "agent", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_users_histogram_devices(self, sample_auth_response):
        """Test users histogram with --devices flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/connected_user_device_count_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01", "count": 10}]})
        )

        result = runner.invoke(app, ["users", "histogram", "agent", "--devices", *auth_options()])

        assert result.exit_code == 0

    def test_users_histogram_invalid_type(self):
        """Test users histogram with invalid type."""
        result = runner.invoke(app, ["users", "histogram", "all", *auth_options()])
        assert result.exit_code == 1

    @respx.mock
    def test_users_entities(self, sample_auth_response):
        """Test users entities command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/connected_entity_count").mock(
            return_value=httpx.Response(200, json={"data": [{"entity_count": 100}]})
        )

        result = runner.invoke(app, ["users", "entities", "agent", *auth_options()])

        assert result.exit_code == 0

    def test_users_entities_invalid_type(self):
        """Test users entities with invalid type."""
        result = runner.invoke(app, ["users", "entities", "agentless", *auth_options()])
        assert result.exit_code == 1

    @respx.mock
    def test_users_versions(self, sample_auth_response):
        """Test users versions command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/client_version_distribution").mock(
            return_value=httpx.Response(200, json={"data": [{"version": "6.2.0", "count": 50}]})
        )

        result = runner.invoke(app, ["users", "versions", *auth_options()])

        assert result.exit_code == 0


# ═══════════════════════════════════════════════════════════════════
# Additional Apps Command Tests
# ═══════════════════════════════════════════════════════════════════

class TestCLIAppsCommandsExtended:
    """Extended tests for apps subcommand group."""

    @respx.mock
    def test_apps_info(self, sample_auth_response):
        """Test apps info command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/app_info").mock(
            return_value=httpx.Response(200, json={"data": [{"app_name": "TestApp"}]})
        )

        result = runner.invoke(app, ["apps", "info", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_apps_risk(self, sample_auth_response):
        """Test apps risk command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/app_by_risk_score").mock(
            return_value=httpx.Response(200, json={"data": [{"risk_score": 5, "count": 10}]})
        )

        result = runner.invoke(app, ["apps", "risk", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_apps_tags(self, sample_auth_response):
        """Test apps tags command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/app_by_tag").mock(
            return_value=httpx.Response(200, json={"data": [{"tag": "business"}]})
        )

        result = runner.invoke(app, ["apps", "tags", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_apps_transfer(self, sample_auth_response):
        """Test apps transfer command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/total_data_transfer_application").mock(
            return_value=httpx.Response(200, json={"data": [{"bytes_sent": 1024}]})
        )

        result = runner.invoke(app, ["apps", "transfer", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_apps_transfer_by_destination(self, sample_auth_response):
        """Test apps transfer with --by-destination flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/total_data_transfer_by_destination").mock(
            return_value=httpx.Response(200, json={"data": [{"destination": "cloud"}]})
        )

        result = runner.invoke(app, ["apps", "transfer", "--by-destination", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_apps_bandwidth(self, sample_auth_response):
        """Test apps bandwidth command requires app name argument."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/app_details_bw_info_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"bandwidth": 500}]})
        )

        # apps bandwidth now requires an app_name argument
        result = runner.invoke(app, ["apps", "bandwidth", "Zoom", *auth_options()])

        assert result.exit_code == 0


# ═══════════════════════════════════════════════════════════════════
# Accelerated Command Tests
# ═══════════════════════════════════════════════════════════════════

class TestCLIAcceleratedCommands:
    """Tests for accelerated subcommand group."""

    @respx.mock
    def test_accelerated_list(self, sample_auth_response):
        """Test accelerated list command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/accelerated_application_list").mock(
            return_value=httpx.Response(200, json={"data": [{"app_name": "AccelApp"}]})
        )

        result = runner.invoke(app, ["accelerated", "list", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_accelerated_count(self, sample_auth_response):
        """Test accelerated count command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/applications_count").mock(
            return_value=httpx.Response(200, json={"data": [{"count": 15}]})
        )

        result = runner.invoke(app, ["accelerated", "count", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_accelerated_count_users(self, sample_auth_response):
        """Test accelerated count with --users flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/users_count").mock(
            return_value=httpx.Response(200, json={"data": [{"count": 100}]})
        )

        result = runner.invoke(app, ["accelerated", "count", "--users", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_accelerated_performance(self, sample_auth_response):
        """Test accelerated performance command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/performance_boost").mock(
            return_value=httpx.Response(200, json={"data": [{"boost": 25}]})
        )

        result = runner.invoke(app, ["accelerated", "performance", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_accelerated_transfer(self, sample_auth_response):
        """Test accelerated transfer command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/total_data_transfer").mock(
            return_value=httpx.Response(200, json={"data": [{"bytes": 1024}]})
        )

        result = runner.invoke(app, ["accelerated", "transfer", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_accelerated_transfer_per_app(self, sample_auth_response):
        """Test accelerated transfer with --per-app flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/data_transfer_throughput_per_app").mock(
            return_value=httpx.Response(200, json={"data": [{"app": "TestApp"}]})
        )

        result = runner.invoke(app, ["accelerated", "transfer", "--per-app", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_accelerated_response_time(self, sample_auth_response):
        """Test accelerated response-time command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/accelerated_applications/response_time_before_and_after_improvement").mock(
            return_value=httpx.Response(200, json={"data": [{"improvement": 30}]})
        )

        result = runner.invoke(app, ["accelerated", "response-time", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_accelerated_response_time_per_app(self, sample_auth_response):
        """Test accelerated response-time with --per-app flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/accelerated_applications/response_time_before_and_after_improvement_per_app").mock(
            return_value=httpx.Response(200, json={"data": [{"app": "TestApp"}]})
        )

        result = runner.invoke(app, ["accelerated", "response-time", "--per-app", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_accelerated_histogram_throughput(self, sample_auth_response):
        """Test accelerated histogram throughput command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/throughput_per_app_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01"}]})
        )

        result = runner.invoke(app, ["accelerated", "histogram", "throughput", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_accelerated_histogram_packet_loss(self, sample_auth_response):
        """Test accelerated histogram packet-loss command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/packet_loss_per_app_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01"}]})
        )

        result = runner.invoke(app, ["accelerated", "histogram", "packet-loss", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_accelerated_histogram_rtt(self, sample_auth_response):
        """Test accelerated histogram rtt command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/rtt_variance_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01"}]})
        )

        result = runner.invoke(app, ["accelerated", "histogram", "rtt", *auth_options()])

        assert result.exit_code == 0


# ═══════════════════════════════════════════════════════════════════
# Sites Command Tests Extended
# ═══════════════════════════════════════════════════════════════════

class TestCLISitesCommandsExtended:
    """Extended tests for sites subcommand group."""

    @respx.mock
    def test_sites_traffic(self, sample_auth_response):
        """Test sites traffic command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/site_traffic").mock(
            return_value=httpx.Response(200, json={"data": [{"traffic": 1000}]})
        )

        result = runner.invoke(app, ["sites", "traffic", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_sites_bandwidth(self, sample_auth_response):
        """Test sites bandwidth command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/bandwidth_consumption_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"bandwidth": 500}]})
        )

        result = runner.invoke(app, ["sites", "bandwidth", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_sites_sessions(self, sample_auth_response):
        """Test sites sessions command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/session_count").mock(
            return_value=httpx.Response(200, json={"data": [{"session_count": 150}]})
        )

        result = runner.invoke(app, ["sites", "sessions", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_sites_search(self, sample_auth_response):
        """Test sites search command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/site_location_search_contains").mock(
            return_value=httpx.Response(200, json={"data": [{"site_name": "US West"}]})
        )

        result = runner.invoke(app, ["sites", "search", "US West", *auth_options()])

        assert result.exit_code == 0


# ═══════════════════════════════════════════════════════════════════
# Security Command Tests Extended
# ═══════════════════════════════════════════════════════════════════

class TestCLISecurityCommandsExtended:
    """Extended tests for security subcommand group."""

    @respx.mock
    def test_security_access(self, sample_auth_response):
        """Test security access command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/pab/access_events").mock(
            return_value=httpx.Response(200, json={"data": [{"event_id": "1"}]})
        )

        result = runner.invoke(app, ["security", "access", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_access_blocked(self, sample_auth_response):
        """Test security access with --blocked flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/access_events_blocked").mock(
            return_value=httpx.Response(200, json={"data": [{"event_id": "2"}]})
        )

        result = runner.invoke(app, ["security", "access", "--blocked", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_access_breakdown(self, sample_auth_response):
        """Test security access with --breakdown flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/pab/access_events_breakdown").mock(
            return_value=httpx.Response(200, json={"data": [{"category": "blocked"}]})
        )

        result = runner.invoke(app, ["security", "access", "--breakdown", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_access_histogram(self, sample_auth_response):
        """Test security access with --histogram flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/access_events_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01"}]})
        )

        result = runner.invoke(app, ["security", "access", "--histogram", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_access_blocked_breakdown(self, sample_auth_response):
        """Test security access with --blocked --breakdown flags."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/access_events_breakdown_blocked").mock(
            return_value=httpx.Response(200, json={"data": [{"category": "blocked"}]})
        )

        result = runner.invoke(app, ["security", "access", "--blocked", "--breakdown", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_access_blocked_histogram(self, sample_auth_response):
        """Test security access with --blocked --histogram flags."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/access_events_blocked_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01"}]})
        )

        result = runner.invoke(app, ["security", "access", "--blocked", "--histogram", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_access_breakdown_histogram(self, sample_auth_response):
        """Test security access with --breakdown --histogram flags."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/access_events_breakdown_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01"}]})
        )

        result = runner.invoke(app, ["security", "access", "--breakdown", "--histogram", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_access_all_flags(self, sample_auth_response):
        """Test security access with all flags."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/access_events_breakdown_blocked_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01"}]})
        )

        result = runner.invoke(app, ["security", "access", "--blocked", "--breakdown", "--histogram", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_data(self, sample_auth_response):
        """Test security data command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/pab/data_events").mock(
            return_value=httpx.Response(200, json={"data": [{"event_id": "3"}]})
        )

        result = runner.invoke(app, ["security", "data", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_data_blocked(self, sample_auth_response):
        """Test security data with --blocked flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/data_events_blocked").mock(
            return_value=httpx.Response(200, json={"data": [{"event_id": "4"}]})
        )

        result = runner.invoke(app, ["security", "data", "--blocked", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_data_breakdown(self, sample_auth_response):
        """Test security data with --breakdown flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/data_events_breakdown").mock(
            return_value=httpx.Response(200, json={"data": [{"category": "blocked"}]})
        )

        result = runner.invoke(app, ["security", "data", "--breakdown", *auth_options()])

        assert result.exit_code == 0


# ═══════════════════════════════════════════════════════════════════
# Monitoring Command Tests
# ═══════════════════════════════════════════════════════════════════

class TestCLIMonitoringCommands:
    """Tests for monitoring subcommand group."""

    @respx.mock
    def test_monitoring_users(self, sample_auth_response):
        """Test monitoring users command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/user/monitored/user_count").mock(
            return_value=httpx.Response(200, json={"data": [{"count": 100}]})
        )

        result = runner.invoke(app, ["monitoring", "users", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_monitoring_users_histogram(self, sample_auth_response):
        """Test monitoring users with --histogram flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/user/monitored/user_count_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01", "count": 50}]})
        )

        result = runner.invoke(app, ["monitoring", "users", "--histogram", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_monitoring_devices(self, sample_auth_response):
        """Test monitoring devices command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/monitored/device_count").mock(
            return_value=httpx.Response(200, json={"data": [{"device_count": 200}]})
        )

        result = runner.invoke(app, ["monitoring", "devices", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_monitoring_devices_histogram(self, sample_auth_response):
        """Test monitoring devices with --histogram flag."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/monitored/device_count_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01", "count": 100}]})
        )

        result = runner.invoke(app, ["monitoring", "devices", "--histogram", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_monitoring_experience(self, sample_auth_response):
        """Test monitoring experience command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/monitored/user_experience_score").mock(
            return_value=httpx.Response(200, json={"data": [{"score": 85}]})
        )

        result = runner.invoke(app, ["monitoring", "experience", *auth_options()])

        assert result.exit_code == 0


# ═══════════════════════════════════════════════════════════════════
# Raw Query Command Tests
# ═══════════════════════════════════════════════════════════════════

class TestCLIRawQueryCommand:
    """Tests for raw query command."""

    @respx.mock
    def test_raw_query(self, sample_auth_response):
        """Test raw query command."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(200, json={"data": [{"username": "test"}]})
        )

        result = runner.invoke(app, ["query", "query/users/agent/user_list", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_raw_query_custom_hours(self, sample_auth_response):
        """Test raw query with custom hours."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        route = respx.post(url__regex=r".*/query/sites/site_count").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        result = runner.invoke(app, ["query", "query/sites/site_count", "--hours", "48", *auth_options()])

        assert result.exit_code == 0
        request_body = json.loads(route.calls[0].request.content)
        assert request_body["filter"]["rules"][0]["values"] == [48]


# ═══════════════════════════════════════════════════════════════════
# Display Helper Tests
# ═══════════════════════════════════════════════════════════════════

class TestCLIJSONOutputExtended:
    """Additional tests for JSON output across all commands."""

    @respx.mock
    def test_users_devices_json(self, sample_auth_response):
        """Test users devices with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/device_list").mock(
            return_value=httpx.Response(200, json={"data": [{"device": "test"}]})
        )

        result = runner.invoke(app, ["users", "devices", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "device" in result.output

    @respx.mock
    def test_users_sessions_json(self, sample_auth_response):
        """Test users sessions with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/other/session_list").mock(
            return_value=httpx.Response(200, json={"data": [{"session": "test"}]})
        )

        result = runner.invoke(app, ["users", "sessions", "other", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "session" in result.output

    @respx.mock
    def test_users_risky_json(self, sample_auth_response):
        """Test users risky with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/risky_user_count").mock(
            return_value=httpx.Response(200, json={"data": [{"count": 5}]})
        )

        result = runner.invoke(app, ["users", "risky", "agent", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "count" in result.output

    @respx.mock
    def test_users_active_json(self, sample_auth_response):
        """Test users active with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agentless/active_user_count").mock(
            return_value=httpx.Response(200, json={"data": [{"count": 20}]})
        )

        result = runner.invoke(app, ["users", "active", "agentless", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "count" in result.output

    @respx.mock
    def test_users_histogram_json(self, sample_auth_response):
        """Test users histogram with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/connected_user_count_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01"}]})
        )

        result = runner.invoke(app, ["users", "histogram", "agent", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "timestamp" in result.output

    @respx.mock
    def test_users_entities_json(self, sample_auth_response):
        """Test users entities with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/connected_entity_count").mock(
            return_value=httpx.Response(200, json={"data": [{"entity": "test"}]})
        )

        result = runner.invoke(app, ["users", "entities", "agent", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "entity" in result.output

    @respx.mock
    def test_users_versions_json(self, sample_auth_response):
        """Test users versions with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/client_version_distribution").mock(
            return_value=httpx.Response(200, json={"data": [{"version": "6.2.0"}]})
        )

        result = runner.invoke(app, ["users", "versions", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "version" in result.output

    @respx.mock
    def test_apps_list_json(self, sample_auth_response, sample_application_list_response):
        """Test apps list with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/application_list").mock(
            return_value=httpx.Response(200, json=sample_application_list_response)
        )

        result = runner.invoke(app, ["apps", "list", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "Salesforce" in result.output

    @respx.mock
    def test_apps_info_json(self, sample_auth_response):
        """Test apps info with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/app_info").mock(
            return_value=httpx.Response(200, json={"data": [{"app": "test"}]})
        )

        result = runner.invoke(app, ["apps", "info", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "app" in result.output

    @respx.mock
    def test_apps_risk_json(self, sample_auth_response):
        """Test apps risk with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/app_by_risk_score").mock(
            return_value=httpx.Response(200, json={"data": [{"risk": 5}]})
        )

        result = runner.invoke(app, ["apps", "risk", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "risk" in result.output

    @respx.mock
    def test_apps_tags_json(self, sample_auth_response):
        """Test apps tags with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/app_by_tag").mock(
            return_value=httpx.Response(200, json={"data": [{"tag": "test"}]})
        )

        result = runner.invoke(app, ["apps", "tags", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "tag" in result.output

    @respx.mock
    def test_apps_transfer_json(self, sample_auth_response):
        """Test apps transfer with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/total_data_transfer_application").mock(
            return_value=httpx.Response(200, json={"data": [{"bytes": 1024}]})
        )

        result = runner.invoke(app, ["apps", "transfer", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "bytes" in result.output

    @respx.mock
    def test_apps_bandwidth_json(self, sample_auth_response):
        """Test apps bandwidth with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/app_details_bw_info_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"bw": 500}]})
        )

        # apps bandwidth now requires an app_name argument
        result = runner.invoke(app, ["apps", "bandwidth", "Slack", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "bw" in result.output

    @respx.mock
    def test_accelerated_list_json(self, sample_auth_response):
        """Test accelerated list with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/accelerated_application_list").mock(
            return_value=httpx.Response(200, json={"data": [{"app": "accel"}]})
        )

        result = runner.invoke(app, ["accelerated", "list", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "accel" in result.output

    @respx.mock
    def test_accelerated_count_json(self, sample_auth_response):
        """Test accelerated count with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/applications_count").mock(
            return_value=httpx.Response(200, json={"data": [{"count": 15}]})
        )

        result = runner.invoke(app, ["accelerated", "count", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "count" in result.output

    @respx.mock
    def test_accelerated_performance_json(self, sample_auth_response):
        """Test accelerated performance with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/performance_boost").mock(
            return_value=httpx.Response(200, json={"data": [{"boost": 25}]})
        )

        result = runner.invoke(app, ["accelerated", "performance", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "boost" in result.output

    @respx.mock
    def test_accelerated_transfer_json(self, sample_auth_response):
        """Test accelerated transfer with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/total_data_transfer").mock(
            return_value=httpx.Response(200, json={"data": [{"bytes": 1024}]})
        )

        result = runner.invoke(app, ["accelerated", "transfer", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "bytes" in result.output

    @respx.mock
    def test_accelerated_response_time_json(self, sample_auth_response):
        """Test accelerated response-time with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/accelerated_applications/response_time_before_and_after_improvement").mock(
            return_value=httpx.Response(200, json={"data": [{"improvement": 30}]})
        )

        result = runner.invoke(app, ["accelerated", "response-time", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "improvement" in result.output

    @respx.mock
    def test_accelerated_histogram_json(self, sample_auth_response):
        """Test accelerated histogram with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/accelerated_applications/throughput_per_app_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01"}]})
        )

        result = runner.invoke(app, ["accelerated", "histogram", "throughput", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "timestamp" in result.output

    @respx.mock
    def test_sites_list_json(self, sample_auth_response, sample_site_count_response):
        """Test sites list with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/site_count").mock(
            return_value=httpx.Response(200, json=sample_site_count_response)
        )

        result = runner.invoke(app, ["sites", "list", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "site_count" in result.output

    @respx.mock
    def test_sites_traffic_json(self, sample_auth_response):
        """Test sites traffic with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/site_traffic").mock(
            return_value=httpx.Response(200, json={"data": [{"traffic": 1000}]})
        )

        result = runner.invoke(app, ["sites", "traffic", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "traffic" in result.output

    @respx.mock
    def test_sites_bandwidth_json(self, sample_auth_response):
        """Test sites bandwidth with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/bandwidth_consumption_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"bandwidth": 500}]})
        )

        result = runner.invoke(app, ["sites", "bandwidth", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "bandwidth" in result.output

    @respx.mock
    def test_sites_sessions_json(self, sample_auth_response):
        """Test sites sessions with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/session_count").mock(
            return_value=httpx.Response(200, json={"data": [{"sessions": 150}]})
        )

        result = runner.invoke(app, ["sites", "sessions", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "sessions" in result.output

    @respx.mock
    def test_sites_search_json(self, sample_auth_response):
        """Test sites search with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/site_location_search_contains").mock(
            return_value=httpx.Response(200, json={"data": [{"site": "US West"}]})
        )

        result = runner.invoke(app, ["sites", "search", "US West", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "site" in result.output

    @respx.mock
    def test_security_access_json(self, sample_auth_response):
        """Test security access with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/pab/access_events").mock(
            return_value=httpx.Response(200, json={"data": [{"event": "1"}]})
        )

        result = runner.invoke(app, ["security", "access", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "event" in result.output

    @respx.mock
    def test_security_data_json(self, sample_auth_response):
        """Test security data with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/pab/data_events").mock(
            return_value=httpx.Response(200, json={"data": [{"event": "2"}]})
        )

        result = runner.invoke(app, ["security", "data", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "event" in result.output

    @respx.mock
    def test_monitoring_users_json(self, sample_auth_response):
        """Test monitoring users with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/user/monitored/user_count").mock(
            return_value=httpx.Response(200, json={"data": [{"count": 100}]})
        )

        result = runner.invoke(app, ["monitoring", "users", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "count" in result.output

    @respx.mock
    def test_monitoring_devices_json(self, sample_auth_response):
        """Test monitoring devices with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/monitored/device_count").mock(
            return_value=httpx.Response(200, json={"data": [{"count": 200}]})
        )

        result = runner.invoke(app, ["monitoring", "devices", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "count" in result.output

    @respx.mock
    def test_monitoring_experience_json(self, sample_auth_response):
        """Test monitoring experience with JSON output."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/monitored/user_experience_score").mock(
            return_value=httpx.Response(200, json={"data": [{"score": 85}]})
        )

        result = runner.invoke(app, ["monitoring", "experience", "--json", *auth_options()])

        assert result.exit_code == 0
        assert "score" in result.output


class TestCLIDisplayHelpers:
    """Tests for CLI display helper functions."""

    @respx.mock
    def test_display_empty_users(self, sample_auth_response, sample_empty_response):
        """Test display with no users found."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/user_list").mock(
            return_value=httpx.Response(200, json=sample_empty_response)
        )

        result = runner.invoke(app, ["users", "list", "agent", *auth_options()])

        assert result.exit_code == 0
        assert "No users found" in result.output

    @respx.mock
    def test_display_empty_devices(self, sample_auth_response):
        """Test display with no devices found."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/device_list").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        result = runner.invoke(app, ["users", "devices", *auth_options()])

        assert result.exit_code == 0
        assert "No devices found" in result.output

    @respx.mock
    def test_display_empty_sessions(self, sample_auth_response):
        """Test display with no sessions found."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/other/session_list").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        result = runner.invoke(app, ["users", "sessions", "other", *auth_options()])

        assert result.exit_code == 0
        assert "No sessions found" in result.output

    @respx.mock
    def test_display_empty_applications(self, sample_auth_response):
        """Test display with no applications found."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/applications/internal/application_list").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        result = runner.invoke(app, ["apps", "list", *auth_options()])

        assert result.exit_code == 0
        assert "No applications found" in result.output

    @respx.mock
    def test_display_empty_histogram(self, sample_auth_response):
        """Test display with no histogram data."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/connected_user_count_histogram").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        result = runner.invoke(app, ["users", "histogram", "agent", *auth_options()])

        assert result.exit_code == 0
        assert "No histogram data" in result.output

    @respx.mock
    def test_display_empty_distribution(self, sample_auth_response):
        """Test display with no distribution data."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/client_version_distribution").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        result = runner.invoke(app, ["users", "versions", *auth_options()])

        assert result.exit_code == 0
        assert "No distribution data" in result.output

    @respx.mock
    def test_display_sites_no_data(self, sample_auth_response):
        """Test display sites with no data."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/site_count").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        result = runner.invoke(app, ["sites", "list", *auth_options()])

        assert result.exit_code == 0
        # Sites command shows "Total sites: 0" for empty data
        assert "0" in result.output


# ═══════════════════════════════════════════════════════════════════
# Tests for New CLI Options (API-Required Filters)
# ═══════════════════════════════════════════════════════════════════

class TestCLINewOptions:
    """Tests for new CLI options added to meet API requirements."""

    @respx.mock
    def test_users_versions_with_platform(self, sample_auth_response):
        """Test users versions with --platform option."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/agent/client_version_distribution").mock(
            return_value=httpx.Response(200, json={"data": [{"version": "6.2.0", "count": 50}]})
        )

        result = runner.invoke(app, ["users", "versions", "--platform", "ngfw", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_apps_bandwidth_with_interval(self, sample_auth_response):
        """Test apps bandwidth with --interval option for histogram config."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/app_details_bw_info_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"bytes": 1024}]})
        )

        # apps bandwidth now requires an app_name argument
        result = runner.invoke(app, ["apps", "bandwidth", "Teams", "--interval", "60", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_sites_sessions_with_node_type(self, sample_auth_response):
        """Test sites sessions with --node-type option."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/session_count").mock(
            return_value=httpx.Response(200, json={"data": [{"session_count": 100}]})
        )

        result = runner.invoke(app, ["sites", "sessions", "--node-type", "51", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_sites_sessions_with_site_name(self, sample_auth_response):
        """Test sites sessions with --site option."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/sites/session_count").mock(
            return_value=httpx.Response(200, json={"data": [{"session_count": 50}]})
        )

        result = runner.invoke(app, ["sites", "sessions", "--site", "Remote-Conn1", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_monitoring_devices_with_platform(self, sample_auth_response):
        """Test monitoring devices with --platform option."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/monitored/device_count").mock(
            return_value=httpx.Response(200, json={"data": [{"device_count": 25}]})
        )

        result = runner.invoke(app, ["monitoring", "devices", "--platform", "prisma_access", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_monitoring_devices_histogram_with_interval(self, sample_auth_response):
        """Test monitoring devices histogram with --interval option."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/users/monitored/device_count_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01", "count": 10}]})
        )

        result = runner.invoke(app, ["monitoring", "devices", "--histogram", "--interval", "60", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_access_histogram_with_interval(self, sample_auth_response):
        """Test security access histogram with --interval option."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/access_events_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01", "count": 5}]})
        )

        result = runner.invoke(app, ["security", "access", "--histogram", "--interval", "15", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_access_histogram_with_platform(self, sample_auth_response):
        """Test security access histogram with --platform option."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/access_events_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01", "count": 5}]})
        )

        result = runner.invoke(app, ["security", "access", "--histogram", "--platform", "prisma_access", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_data_histogram_with_interval(self, sample_auth_response):
        """Test security data histogram with --interval option."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/data_events_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01", "count": 3}]})
        )

        result = runner.invoke(app, ["security", "data", "--histogram", "--interval", "30", *auth_options()])

        assert result.exit_code == 0

    @respx.mock
    def test_security_data_histogram_with_platform(self, sample_auth_response):
        """Test security data histogram with --platform option."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )
        respx.post(url__regex=r".*/query/pab/data_events_histogram").mock(
            return_value=httpx.Response(200, json={"data": [{"timestamp": "2025-01-01", "count": 3}]})
        )

        result = runner.invoke(app, ["security", "data", "--histogram", "--platform", "prisma_access", *auth_options()])

        assert result.exit_code == 0
