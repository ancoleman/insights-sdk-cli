"""
Prisma Access Insights SDK

A Python SDK for querying the Palo Alto Networks Prisma Access Insights 3.0 API.
"""

__version__ = "0.1.0"

from .client import InsightsClient, AsyncInsightsClient
from .auth import AuthClient, AsyncAuthClient
from .models import (
    FilterRule,
    QueryFilter,
    QueryRequest,
    Operator,
    Region,
    PaginatedResponse,
    UserInfo,
    ApplicationInfo,
    ThreatInfo,
    HealthStatus,
)

__all__ = [
    "InsightsClient",
    "AsyncInsightsClient",
    "AuthClient",
    "AsyncAuthClient",
    "FilterRule",
    "QueryFilter",
    "QueryRequest",
    "Operator",
    "Region",
    "PaginatedResponse",
    "UserInfo",
    "ApplicationInfo",
    "ThreatInfo",
    "HealthStatus",
]
