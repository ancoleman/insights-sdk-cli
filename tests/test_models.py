"""
Unit tests for insights_sdk.models module.

Tests the Pydantic models, enums, and query building functionality.
"""

import pytest
from datetime import datetime

from insights_sdk.models import (
    Region,
    Operator,
    FilterRule,
    QueryFilter,
    QueryRequest,
    PaginatedResponse,
    UserInfo,
    ApplicationInfo,
    ThreatInfo,
    HealthStatus,
)


class TestRegionEnum:
    """Tests for Region enum."""

    def test_region_values(self):
        """Test that all regions have correct string values."""
        assert Region.AMERICAS.value == "americas"
        assert Region.EUROPE.value == "europe"
        assert Region.ASIA.value == "asia"
        assert Region.APAC.value == "apac"

    def test_region_from_string(self):
        """Test creating Region from string value."""
        assert Region("americas") == Region.AMERICAS
        assert Region("europe") == Region.EUROPE
        assert Region("asia") == Region.ASIA
        assert Region("apac") == Region.APAC

    def test_region_is_string_subclass(self):
        """Test that Region values can be used as strings."""
        assert isinstance(Region.AMERICAS, str)
        assert Region.AMERICAS == "americas"


class TestOperatorEnum:
    """Tests for Operator enum."""

    def test_list_operators(self):
        """Test list membership operators."""
        assert Operator.IN.value == "in"
        assert Operator.NOT_IN.value == "not_in"

    def test_equality_operators(self):
        """Test equality operators."""
        assert Operator.EQUALS.value == "equals"
        assert Operator.NOT_EQUALS.value == "not_equals"

    def test_comparison_operators(self):
        """Test comparison operators."""
        assert Operator.GREATER_THAN.value == "greater_than"
        assert Operator.LESS_THAN.value == "less_than"
        assert Operator.GREATER_THAN_OR_EQUALS.value == "greater_than_or_equals"
        assert Operator.LESS_THAN_OR_EQUALS.value == "less_than_or_equals"

    def test_string_operators(self):
        """Test string matching operators."""
        assert Operator.CONTAINS.value == "contains"
        assert Operator.NOT_CONTAINS.value == "not_contains"
        assert Operator.STARTS_WITH.value == "starts_with"
        assert Operator.ENDS_WITH.value == "ends_with"

    def test_time_operators(self):
        """Test time range operators."""
        assert Operator.LAST_N_HOURS.value == "last_n_hours"
        assert Operator.LAST_N_DAYS.value == "last_n_days"
        assert Operator.BETWEEN.value == "between"


class TestFilterRule:
    """Tests for FilterRule model."""

    def test_create_filter_rule(self):
        """Test creating a filter rule."""
        rule = FilterRule(
            property="username",
            operator=Operator.IN,
            values=["john.doe", "jane.smith"],
        )
        assert rule.property == "username"
        assert rule.operator == Operator.IN
        assert rule.values == ["john.doe", "jane.smith"]

    def test_filter_rule_with_enum_value(self):
        """Test that operator enum is serialized correctly."""
        rule = FilterRule(
            property="source_country",
            operator=Operator.EQUALS,
            values=["US"],
        )
        # With use_enum_values=True, should serialize as string
        data = rule.model_dump()
        assert data["operator"] == "equals"

    def test_filter_rule_with_numbers(self):
        """Test filter rule with numeric values."""
        rule = FilterRule(
            property="risk_score",
            operator=Operator.GREATER_THAN,
            values=[3],
        )
        assert rule.values == [3]

    def test_filter_rule_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(Exception):  # ValidationError
            FilterRule(property="test")

        with pytest.raises(Exception):
            FilterRule(property="test", operator=Operator.IN)


class TestQueryFilter:
    """Tests for QueryFilter model."""

    def test_empty_query_filter(self):
        """Test creating empty query filter."""
        qf = QueryFilter()
        assert qf.rules == []

    def test_query_filter_with_rules(self):
        """Test creating query filter with rules."""
        rules = [
            FilterRule(property="username", operator=Operator.IN, values=["test"]),
            FilterRule(property="source_country", operator=Operator.EQUALS, values=["US"]),
        ]
        qf = QueryFilter(rules=rules)
        assert len(qf.rules) == 2
        assert qf.rules[0].property == "username"
        assert qf.rules[1].property == "source_country"


class TestQueryRequest:
    """Tests for QueryRequest model."""

    def test_empty_query_request(self):
        """Test creating empty query request."""
        qr = QueryRequest()
        assert qr.filter is None

    def test_add_time_filter(self):
        """Test adding time filter."""
        qr = QueryRequest()
        qr.add_time_filter(hours=48)

        assert qr.filter is not None
        assert len(qr.filter.rules) == 1
        assert qr.filter.rules[0].property == "event_time"
        assert qr.filter.rules[0].operator == Operator.LAST_N_HOURS
        assert qr.filter.rules[0].values == [48]

    def test_add_time_filter_default_hours(self):
        """Test default hours value."""
        qr = QueryRequest()
        qr.add_time_filter()  # Uses default 24 hours

        assert qr.filter.rules[0].values == [24]

    def test_add_time_filter_chaining(self):
        """Test that add_time_filter returns self for chaining."""
        qr = QueryRequest()
        result = qr.add_time_filter(24)
        assert result is qr

    def test_add_filter(self):
        """Test adding a custom filter."""
        qr = QueryRequest()
        qr.add_filter(
            property="source_country",
            operator=Operator.IN,
            values=["US", "CA"],
        )

        assert qr.filter is not None
        assert len(qr.filter.rules) == 1
        assert qr.filter.rules[0].property == "source_country"

    def test_add_filter_chaining(self):
        """Test method chaining with add_filter."""
        qr = QueryRequest()
        result = (
            qr.add_time_filter(24)
            .add_filter("source_country", Operator.IN, ["US"])
            .add_filter("platform_type", Operator.EQUALS, ["prisma_access"])
        )

        assert result is qr
        assert len(qr.filter.rules) == 3

    def test_add_multiple_filters(self):
        """Test adding multiple filters."""
        qr = QueryRequest()
        qr.add_time_filter(24)
        qr.add_filter("username", Operator.CONTAINS, ["admin"])
        qr.add_filter("risk_score", Operator.GREATER_THAN, [3])

        assert len(qr.filter.rules) == 3


class TestPaginatedResponse:
    """Tests for PaginatedResponse model."""

    def test_empty_response(self):
        """Test creating response with no pagination info."""
        pr = PaginatedResponse()
        assert pr.total is None
        assert pr.offset is None
        assert pr.limit is None

    def test_full_response(self):
        """Test creating response with all pagination info."""
        pr = PaginatedResponse(total=100, offset=20, limit=10)
        assert pr.total == 100
        assert pr.offset == 20
        assert pr.limit == 10


class TestUserInfo:
    """Tests for UserInfo model."""

    def test_empty_user(self):
        """Test creating user with no data."""
        user = UserInfo()
        assert user.username is None
        assert user.device_name is None

    def test_full_user(self):
        """Test creating user with all fields."""
        user = UserInfo(
            username="john.doe@example.com",
            device_name="LAPTOP-001",
            platform_type="prisma_access",
            agent_version="6.2.0",
            client_os_version="Windows 11",
            source_city="San Francisco",
            source_country="US",
            event_time=datetime(2025, 11, 26, 14, 30, 0),
        )
        assert user.username == "john.doe@example.com"
        assert user.device_name == "LAPTOP-001"
        assert user.platform_type == "prisma_access"
        assert user.source_country == "US"


class TestApplicationInfo:
    """Tests for ApplicationInfo model."""

    def test_empty_app(self):
        """Test creating app with no data."""
        app = ApplicationInfo()
        assert app.app_name is None
        assert app.risk_score is None

    def test_full_app(self):
        """Test creating app with all fields."""
        app = ApplicationInfo(
            app_name="Salesforce",
            app_category="business-systems",
            risk_score=2,
            bytes_sent=1024000,
            bytes_received=2048000,
            sessions=150,
        )
        assert app.app_name == "Salesforce"
        assert app.risk_score == 2
        assert app.sessions == 150


class TestThreatInfo:
    """Tests for ThreatInfo model."""

    def test_empty_threat(self):
        """Test creating threat with no data."""
        threat = ThreatInfo()
        assert threat.threat_name is None
        assert threat.severity is None

    def test_full_threat(self):
        """Test creating threat with all fields."""
        threat = ThreatInfo(
            threat_name="Malware-XYZ",
            threat_type="virus",
            severity="critical",
            action="blocked",
            source_ip="192.168.1.100",
            destination_ip="10.0.0.50",
            event_time=datetime(2025, 11, 26, 14, 30, 0),
        )
        assert threat.threat_name == "Malware-XYZ"
        assert threat.severity == "critical"
        assert threat.action == "blocked"


class TestHealthStatus:
    """Tests for HealthStatus model."""

    def test_minimal_health(self):
        """Test creating health status with required fields only."""
        health = HealthStatus(status="healthy")
        assert health.status == "healthy"
        assert health.message is None
        assert health.details is None

    def test_full_health(self):
        """Test creating health status with all fields."""
        health = HealthStatus(
            status="degraded",
            message="Database connection slow",
            details={"latency_ms": 500, "connection_pool": "exhausted"},
        )
        assert health.status == "degraded"
        assert health.message == "Database connection slow"
        assert health.details["latency_ms"] == 500
