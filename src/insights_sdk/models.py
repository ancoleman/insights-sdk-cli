"""
Data models for Prisma Access Insights API.

These models represent the common request/response structures used across
the Insights API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Region(str, Enum):
    """Supported regions for Insights API."""
    AMERICAS = "americas"
    EUROPE = "europe"
    ASIA = "asia"
    APAC = "apac"


class Operator(str, Enum):
    """Filter operators supported by Insights API."""
    IN = "in"
    NOT_IN = "not_in"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUALS = "greater_than_or_equals"
    LESS_THAN_OR_EQUALS = "less_than_or_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    LAST_N_HOURS = "last_n_hours"
    LAST_N_DAYS = "last_n_days"
    BETWEEN = "between"


class FilterRule(BaseModel):
    """A single filter rule for queries."""
    property: str = Field(..., description="The property/field to filter on")
    operator: Operator = Field(..., description="The filter operator")
    values: list[Any] = Field(..., description="The values to filter by")

    class Config:
        use_enum_values = True


class QueryFilter(BaseModel):
    """Query filter containing multiple rules."""
    rules: list[FilterRule] = Field(default_factory=list, description="List of filter rules")


class QueryRequest(BaseModel):
    """Base query request model."""
    filter: Optional[QueryFilter] = Field(None, description="Optional query filter")

    def add_time_filter(self, hours: int = 24) -> "QueryRequest":
        """Add a time filter for the last N hours.

        Args:
            hours: Number of hours to look back (default: 24)

        Returns:
            Self for method chaining.
        """
        if self.filter is None:
            self.filter = QueryFilter(rules=[])

        self.filter.rules.append(
            FilterRule(
                property="event_time",
                operator=Operator.LAST_N_HOURS,
                values=[hours],
            )
        )
        return self

    def add_filter(
        self,
        property: str,
        operator: Operator,
        values: list[Any],
    ) -> "QueryRequest":
        """Add a filter rule.

        Args:
            property: The property to filter on
            operator: The filter operator
            values: The values to filter by

        Returns:
            Self for method chaining.
        """
        if self.filter is None:
            self.filter = QueryFilter(rules=[])

        self.filter.rules.append(
            FilterRule(property=property, operator=operator, values=values)
        )
        return self


class PaginatedResponse(BaseModel):
    """Base paginated response model."""
    total: Optional[int] = Field(None, description="Total number of results")
    offset: Optional[int] = Field(None, description="Current offset")
    limit: Optional[int] = Field(None, description="Results per page")


class UserInfo(BaseModel):
    """User information from agent/branch queries."""
    username: Optional[str] = None
    device_name: Optional[str] = None
    platform_type: Optional[str] = None
    agent_version: Optional[str] = None
    client_os_version: Optional[str] = None
    source_city: Optional[str] = None
    source_country: Optional[str] = None
    event_time: Optional[datetime] = None


class ApplicationInfo(BaseModel):
    """Application information from app queries."""
    app_name: Optional[str] = None
    app_category: Optional[str] = None
    risk_score: Optional[int] = None
    bytes_sent: Optional[int] = None
    bytes_received: Optional[int] = None
    sessions: Optional[int] = None


class ThreatInfo(BaseModel):
    """Threat information from security queries."""
    threat_name: Optional[str] = None
    threat_type: Optional[str] = None
    severity: Optional[str] = None
    action: Optional[str] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    event_time: Optional[datetime] = None


class HealthStatus(BaseModel):
    """Health status information."""
    status: str
    message: Optional[str] = None
    details: Optional[dict[str, Any]] = None
