"""
Main client for Prisma Access Insights 3.0 API.

Provides methods for querying various insights data including users, applications,
sites, and security events.
"""

import time
import logging
from typing import Any, Optional
from enum import Enum

import httpx

from .auth import (
    AuthClient,
    AsyncAuthClient,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_WRITE_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF,
    RETRYABLE_EXCEPTIONS,
    RETRYABLE_STATUS_CODES,
)
from .models import (
    Region,
    QueryRequest,
    QueryFilter,
    FilterRule,
    Operator,
    PaginatedResponse,
)


logger = logging.getLogger(__name__)


class InsightsClient:
    """Synchronous client for Prisma Access Insights 3.0 API."""

    DEFAULT_BASE_URL = "https://api.strata.paloaltonetworks.com"
    API_VERSION = "v3.0"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tsg_id: str,
        region: Region = Region.AMERICAS,
        base_url: Optional[str] = None,
        timeout: Optional[httpx.Timeout] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
    ):
        """Initialize the Insights client.

        Args:
            client_id: OAuth2 client ID (service account email)
            client_secret: OAuth2 client secret
            tsg_id: Tenant Service Group ID
            region: API region (americas, europe, asia, apac)
            base_url: Optional custom base URL
            timeout: Optional httpx.Timeout configuration
            max_retries: Maximum number of retry attempts (default: 3)
            retry_backoff: Initial retry backoff in seconds (default: 1.0)
        """
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.region = region
        self.tsg_id = tsg_id
        self.timeout = timeout or httpx.Timeout(
            connect=DEFAULT_CONNECT_TIMEOUT,
            read=DEFAULT_READ_TIMEOUT,
            write=DEFAULT_WRITE_TIMEOUT,
            pool=DEFAULT_READ_TIMEOUT,
        )
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        self._auth = AuthClient(
            client_id=client_id,
            client_secret=client_secret,
            tsg_id=tsg_id,
            timeout=self.timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
        )
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with auth token."""
        return {
            "Authorization": f"Bearer {self._auth.get_token()}",
            "Content-Type": "application/json",
            "X-PANW-Region": self.region.value,
        }

    def _build_url(self, endpoint: str) -> str:
        """Build full URL for an endpoint."""
        return f"{self.base_url}/insights/{self.API_VERSION}/resource/{endpoint}"

    def _post(self, endpoint: str, body: Optional[dict] = None) -> dict[str, Any]:
        """Make a POST request to the API with automatic retry.

        Args:
            endpoint: API endpoint path (after /insights/v3.0/resource/)
            body: Request body

        Returns:
            Response JSON as dict

        Raises:
            httpx.HTTPError: If request fails after all retries
        """
        url = self._build_url(endpoint)
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self._get_client().post(
                    url,
                    headers=self._get_headers(),
                    json=body or {},
                )

                # Check for retryable status codes
                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt < self.max_retries:
                        backoff = self.retry_backoff * (2 ** attempt)
                        logger.warning(
                            f"API request to {endpoint} failed with status {response.status_code}, "
                            f"retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(backoff)
                        continue

                response.raise_for_status()
                return response.json()

            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                if attempt < self.max_retries:
                    backoff = self.retry_backoff * (2 ** attempt)
                    logger.warning(
                        f"API request to {endpoint} failed with {type(e).__name__}: {e}, "
                        f"retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(backoff)
                else:
                    logger.error(
                        f"API request to {endpoint} failed after {self.max_retries + 1} attempts: {e}"
                    )
                    raise

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("API request failed unexpectedly")

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "InsightsClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # ========== User Queries ==========

    def get_agent_users(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of agent users.

        Args:
            hours: Number of hours to look back (default: 24)
            filters: Additional filter rules

        Returns:
            User list response
        """
        body = self._build_query_body(hours, filters)
        return self._post("query/users/agent/user_list", body)

    def get_branch_users(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of branch users."""
        body = self._build_query_body(hours, filters)
        return self._post("query/users/branch/user_list", body)

    def get_agentless_users(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of agentless users."""
        body = self._build_query_body(hours, filters)
        return self._post("query/users/agentless/users", body)

    def get_eb_users(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of Enterprise Browser users."""
        body = self._build_query_body(hours, filters)
        return self._post("query/users/eb/user_list", body)

    def get_other_users(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of other/host users."""
        body = self._build_query_body(hours, filters)
        return self._post("query/users/other/user_list", body)

    def get_all_users(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of all users across all connection types."""
        body = self._build_query_body(hours, filters)
        return self._post("query/users/all/user_list_all", body)

    def get_connected_user_count(
        self,
        user_type: str = "agent",
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get count of connected users.

        Args:
            user_type: Type of users. Valid values are: agent, branch, agentless, eb.
                       Note: "all" and "other" are not valid for this endpoint and
                       will result in a 400 error from the API.
            hours: Number of hours to look back
            filters: Additional filter rules
        """
        body = self._build_query_body(hours, filters)
        return self._post(f"query/users/{user_type}/connected_user_count", body)

    def get_user_count_histogram(
        self,
        user_type: str = "agent",
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
        interval: int = 30,
    ) -> dict[str, Any]:
        """Get user count over time as histogram.

        Args:
            user_type: Type of users (agent, branch, agentless, other)
            hours: Number of hours to look back
            filters: Additional filter rules
            interval: Histogram interval in minutes (default: 30)
        """
        body = self._build_query_body(hours, filters)
        body["histogram"] = {
            "enableEmptyInterval": True,
            "property": "event_time",
            "range": "minute",
            "value": interval,
        }
        if user_type == "agent":
            return self._post("query/users/agent/connected_user_count_histogram", body)
        return self._post(f"query/users/{user_type}/user_count_histogram", body)

    def get_agent_devices(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of agent devices."""
        body = self._build_query_body(hours, filters)
        return self._post("query/users/agent/device_list", body)

    def get_agent_sessions(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of agent user sessions.

        Note: Requires a ``username`` filter for agent sessions.
        """
        body = self._build_query_body(hours, filters)
        return self._post("query/users/agent/session_list", body)

    def get_user_sessions(
        self,
        user_type: str = "other",
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get user sessions for any user type.

        Args:
            user_type: One of 'agent', 'agentless', 'branch', 'other'.
                       Agent type requires a ``username`` filter.
                       EB type is not supported for sessions.
            hours: Number of hours to look back
            filters: Additional filter rules
        """
        body = self._build_query_body(hours, filters)
        return self._post(f"query/users/{user_type}/session_list", body)

    def get_risky_user_count(
        self,
        user_type: str = "agent",
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get count of risky users."""
        body = self._build_query_body(hours, filters)
        if user_type == "agent":
            return self._post("query/users/agent/risky_user_count", body)
        return self._post(f"query/{user_type}/risky_user_count", body)

    def get_active_user_count(
        self,
        user_type: str = "agentless",
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get count of active users (agentless, branch, eb, other)."""
        body = self._build_query_body(hours, filters)
        return self._post(f"query/users/{user_type}/active_user_count", body)

    def get_active_users(
        self,
        user_type: str = "agentless",
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of active users (agentless, branch, eb, other)."""
        body = self._build_query_body(hours, filters)
        return self._post(f"query/users/{user_type}/active_user_list", body)

    def get_entity_count(
        self,
        user_type: str = "agent",
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get connected entity count (agent, branch, other)."""
        body = self._build_query_body(hours, filters)
        return self._post(f"query/users/{user_type}/connected_entity_count", body)

    def get_client_version_distribution(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get agent client version distribution.

        Note: Requires ``client_agent_type`` and ``platform_type`` filters.
        """
        body = self._build_query_body(hours, filters)
        return self._post("query/users/agent/client_version_distribution", body)

    def get_unique_device_connections(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get unique device connections list."""
        body = self._build_query_body(hours, filters)
        return self._post("query/users/agent/unique_device_connections_list", body)

    def get_current_user_count(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get current connected user count (agent only, requires platform_type filter)."""
        body = self._build_query_body(hours, filters)
        return self._post("query/users/agent/current_connected_user_count", body)

    def get_device_count_histogram(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
        interval: int = 30,
    ) -> dict[str, Any]:
        """Get agent device count histogram over time."""
        body = self._build_query_body(hours, filters)
        body["histogram"] = {
            "enableEmptyInterval": True,
            "property": "event_time",
            "range": "minute",
            "value": interval,
        }
        return self._post("query/users/agent/connected_user_device_count_histogram", body)

    def get_monitored_user_count(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get count of monitored users.

        Note: Known API limitation — may return DATA10003 on some tenants.
        """
        body = self._build_query_body(hours, filters)
        return self._post("query/user/monitored/user_count", body)

    def get_user_experience_score(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get user experience scores."""
        body = self._build_query_body(hours, filters)
        return self._post("query/users/monitored/user_experience_score", body)

    # ========== Application Queries ==========

    def get_applications(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of internal applications."""
        body = self._build_query_body(hours, filters)
        return self._post("query/applications/internal/application_list", body)

    def get_app_info(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get application information."""
        body = self._build_query_body(hours, filters)
        return self._post("query/applications/app_info", body)

    def get_apps_by_risk_score(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get applications grouped by risk score."""
        body = self._build_query_body(hours, filters)
        return self._post("query/applications/internal/app_by_risk_score", body)

    def get_apps_by_tag(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get applications grouped by tag."""
        body = self._build_query_body(hours, filters)
        return self._post("query/applications/internal/app_by_tag", body)

    def get_app_data_transfer(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get total data transfer by application."""
        body = self._build_query_body(hours, filters)
        return self._post("query/applications/internal/total_data_transfer_application", body)

    def get_accelerated_applications(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of accelerated applications.

        Note: Requires accelerated apps feature enabled on the tenant. Returns DATA10003 if not available.
        """
        body = self._build_query_body(hours, filters)
        return self._post("query/accelerated_applications/accelerated_application_list", body)

    def get_accelerated_app_performance(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get accelerated application performance boost metrics.

        Note: Requires accelerated apps feature enabled on the tenant. Returns DATA10003 if not available.
        """
        body = self._build_query_body(hours, filters)
        return self._post("query/accelerated_applications/performance_boost", body)

    def get_app_bandwidth(
        self,
        app_name: str,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
        interval: int = 30,
    ) -> dict[str, Any]:
        """Get bandwidth histogram for a specific application.

        Args:
            app_name: Application name (e.g., 'Zoom', 'Slack')
            hours: Number of hours to look back
            filters: Additional filter rules
            interval: Histogram interval in minutes (default: 30)
        """
        all_filters = [FilterRule(property="app", operator=Operator.IN, values=[app_name])]
        if filters:
            all_filters.extend(filters)
        body = self._build_query_body(hours, all_filters)
        body["histogram"] = {
            "enableEmptyInterval": True,
            "property": "event_time",
            "range": "minute",
            "value": interval,
        }
        return self._post("query/app_details_bw_info_histogram", body)

    def get_app_data_transfer_by_destination(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get total data transfer grouped by destination."""
        body = self._build_query_body(hours, filters)
        return self._post("query/applications/internal/total_data_transfer_by_destination", body)

    def get_accelerated_app_count(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get count of accelerated applications.

        Note: Requires accelerated apps feature enabled on the tenant. Returns DATA10003 if not available.
        """
        body = self._build_query_body(hours, filters)
        return self._post("query/accelerated_applications/applications_count", body)

    def get_accelerated_user_count(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get count of users on accelerated applications.

        Note: Requires accelerated apps feature enabled on the tenant. Returns DATA10003 if not available.
        """
        body = self._build_query_body(hours, filters)
        return self._post("query/accelerated_applications/users_count", body)

    def get_accelerated_data_transfer(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
        per_app: bool = False,
    ) -> dict[str, Any]:
        """Get data transfer metrics for accelerated apps.

        Note: Requires accelerated apps feature enabled on the tenant. Returns DATA10003 if not available.

        Args:
            hours: Number of hours to look back
            filters: Additional filter rules
            per_app: If True, return throughput per app instead of total
        """
        body = self._build_query_body(hours, filters)
        endpoint = "query/accelerated_applications/data_transfer_throughput_per_app" if per_app else "query/accelerated_applications/total_data_transfer"
        return self._post(endpoint, body)

    def get_accelerated_response_time(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
        per_app: bool = False,
    ) -> dict[str, Any]:
        """Get response time improvement metrics for accelerated apps.

        Note: Requires accelerated apps feature enabled on the tenant. Returns DATA10003 if not available.

        Args:
            hours: Number of hours to look back
            filters: Additional filter rules
            per_app: If True, return per-app breakdown
        """
        body = self._build_query_body(hours, filters)
        if per_app:
            endpoint = "query/applications/accelerated_applications/response_time_before_and_after_improvement_per_app"
        else:
            endpoint = "query/applications/accelerated_applications/response_time_before_and_after_improvement"
        return self._post(endpoint, body)

    def get_accelerated_histogram(
        self,
        metric: str = "throughput",
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
        interval: int = 30,
    ) -> dict[str, Any]:
        """Get histogram for accelerated app metrics.

        Note: Requires accelerated apps feature enabled on the tenant. Returns DATA10003 if not available.

        Args:
            metric: One of 'throughput', 'packet-loss', 'rtt', 'boost'
            hours: Number of hours to look back
            filters: Additional filter rules
            interval: Histogram interval in minutes (default: 30)
        """
        endpoint_map = {
            "throughput": "query/accelerated_applications/throughput_per_app_histogram",
            "packet-loss": "query/accelerated_applications/packet_loss_per_app_histogram",
            "rtt": "query/accelerated_applications/rtt_variance_histogram",
            "boost": "query/accelerated_applications/accelerated_applications/throughput_before_after_boost_histogram",
        }
        body = self._build_query_body(hours, filters)
        body["histogram"] = {
            "enableEmptyInterval": True,
            "property": "event_time",
            "range": "minute",
            "value": interval,
        }
        return self._post(endpoint_map[metric], body)

    # ========== Site Queries ==========

    def get_site_count(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get count of sites."""
        body = self._build_query_body(hours, filters)
        return self._post("query/sites/site_count", body)

    def get_site_traffic(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get site traffic information."""
        body = self._build_query_body(hours, filters)
        return self._post("query/sites/site_traffic", body)

    def get_site_bandwidth(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
        interval: int = 30,
    ) -> dict[str, Any]:
        """Get site bandwidth consumption histogram.

        Args:
            hours: Number of hours to look back
            filters: Additional filter rules
            interval: Histogram interval in minutes (default: 30)
        """
        body = self._build_query_body(hours, filters)
        body["histogram"] = {
            "enableEmptyInterval": True,
            "property": "event_time",
            "range": "minute",
            "value": interval,
        }
        return self._post("query/sites/bandwidth_consumption_histogram", body)

    def get_site_session_count(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get site session count.

        Note: Known API limitation — may return GCP10002 backend error on some tenants.
        """
        body = self._build_query_body(hours, filters)
        return self._post("query/sites/session_count", body)

    def search_sites(
        self,
        search_term: str,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Search for sites by location."""
        body = self._build_query_body(hours, filters)
        body["search"] = search_term
        return self._post("query/sites/site_location_search_contains", body)

    # ========== PAB (Private Access Browser) Queries ==========

    def get_pab_access_events(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get PAB access events."""
        body = self._build_query_body(hours, filters)
        return self._post("query/applications/pab/access_events", body)

    def get_monitored_device_count(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get count of monitored devices."""
        body = self._build_query_body(hours, filters)
        return self._post("query/users/monitored/device_count", body)

    def get_monitored_device_count_histogram(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
        interval: int = 30,
    ) -> dict[str, Any]:
        """Get monitored device count histogram over time."""
        body = self._build_query_body(hours, filters)
        body["histogram"] = {
            "enableEmptyInterval": True,
            "property": "event_time",
            "range": "minute",
            "value": interval,
        }
        return self._post("query/users/monitored/device_count_histogram", body)

    def get_pab_access_events_breakdown(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get PAB access events breakdown."""
        body = self._build_query_body(hours, filters)
        return self._post("query/applications/pab/access_events_breakdown", body)

    def get_pab_access_events_blocked(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get blocked PAB access events."""
        body = self._build_query_body(hours, filters)
        return self._post("query/applications/pab/access_events_blocked", body)

    def get_pab_data_events(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get PAB data events."""
        body = self._build_query_body(hours, filters)
        return self._post("query/applications/pab/data_events", body)

    def get_pab_data_events_blocked(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get blocked PAB data events."""
        body = self._build_query_body(hours, filters)
        return self._post("query/pab/data_events_blocked", body)

    def get_pab_data_events_breakdown(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get PAB data events breakdown."""
        body = self._build_query_body(hours, filters)
        return self._post("query/pab/data_events_breakdown", body)

    # ========== Export Queries ==========

    def export_agent_users(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Export agent user list (for large datasets)."""
        body = self._build_query_body(hours, filters)
        return self._post("export/query/users/agent/user_list", body)

    def export_branch_users(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Export branch user list (for large datasets)."""
        body = self._build_query_body(hours, filters)
        return self._post("export/query/users/branch/user_list", body)

    # ========== Helper Methods ==========

    def _build_query_body(
        self,
        hours: int,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Build a query request body.

        Args:
            hours: Number of hours to look back
            filters: Additional filter rules

        Returns:
            Query body dict
        """
        rules = [
            {
                "property": "event_time",
                "operator": "last_n_hours",
                "values": [hours],
            }
        ]

        if filters:
            for f in filters:
                rules.append({
                    "property": f.property,
                    "operator": f.operator.value if isinstance(f.operator, Operator) else f.operator,
                    "values": f.values,
                })

        return {"filter": {"rules": rules}}

    def filter(
        self,
        property: str,
        operator: Operator,
        values: list[Any],
    ) -> FilterRule:
        """Create a filter rule for queries.

        Args:
            property: Property/field to filter on
            operator: Filter operator
            values: Values to filter by

        Returns:
            FilterRule instance

        Example:
            >>> client.get_agent_users(filters=[
            ...     client.filter("username", Operator.IN, ["john.doe"]),
            ...     client.filter("source_country", Operator.EQUALS, ["US"]),
            ... ])
        """
        return FilterRule(property=property, operator=operator, values=values)


class AsyncInsightsClient:
    """Asynchronous client for Prisma Access Insights 3.0 API."""

    DEFAULT_BASE_URL = "https://api.strata.paloaltonetworks.com"
    API_VERSION = "v3.0"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tsg_id: str,
        region: Region = Region.AMERICAS,
        base_url: Optional[str] = None,
        timeout: Optional[httpx.Timeout] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
    ):
        """Initialize the async Insights client.

        Args:
            client_id: OAuth2 client ID (service account email)
            client_secret: OAuth2 client secret
            tsg_id: Tenant Service Group ID
            region: API region (americas, europe, asia, apac)
            base_url: Optional custom base URL
            timeout: Optional httpx.Timeout configuration
            max_retries: Maximum number of retry attempts (default: 3)
            retry_backoff: Initial retry backoff in seconds (default: 1.0)
        """
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.region = region
        self.tsg_id = tsg_id
        self.timeout = timeout or httpx.Timeout(
            connect=DEFAULT_CONNECT_TIMEOUT,
            read=DEFAULT_READ_TIMEOUT,
            write=DEFAULT_WRITE_TIMEOUT,
            pool=DEFAULT_READ_TIMEOUT,
        )
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        self._auth = AsyncAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            tsg_id=tsg_id,
            timeout=self.timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
        )
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def _get_headers(self) -> dict[str, str]:
        """Get request headers with auth token."""
        token = await self._auth.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-PANW-Region": self.region.value,
        }

    def _build_url(self, endpoint: str) -> str:
        """Build full URL for an endpoint."""
        return f"{self.base_url}/insights/{self.API_VERSION}/resource/{endpoint}"

    async def _post(self, endpoint: str, body: Optional[dict] = None) -> dict[str, Any]:
        """Make an async POST request to the API with automatic retry.

        Args:
            endpoint: API endpoint path (after /insights/v3.0/resource/)
            body: Request body

        Returns:
            Response JSON as dict

        Raises:
            httpx.HTTPError: If request fails after all retries
        """
        import asyncio

        url = self._build_url(endpoint)
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                client = await self._get_client()
                headers = await self._get_headers()
                response = await client.post(url, headers=headers, json=body or {})

                # Check for retryable status codes
                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt < self.max_retries:
                        backoff = self.retry_backoff * (2 ** attempt)
                        logger.warning(
                            f"Async API request to {endpoint} failed with status {response.status_code}, "
                            f"retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(backoff)
                        continue

                response.raise_for_status()
                return response.json()

            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                if attempt < self.max_retries:
                    backoff = self.retry_backoff * (2 ** attempt)
                    logger.warning(
                        f"Async API request to {endpoint} failed with {type(e).__name__}: {e}, "
                        f"retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        f"Async API request to {endpoint} failed after {self.max_retries + 1} attempts: {e}"
                    )
                    raise

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Async API request failed unexpectedly")

    async def close(self) -> None:
        """Close the async HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "AsyncInsightsClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    # Async versions of all the same methods
    async def get_agent_users(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of agent users."""
        body = self._build_query_body(hours, filters)
        return await self._post("query/users/agent/user_list", body)

    async def get_all_users(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of all users."""
        body = self._build_query_body(hours, filters)
        return await self._post("query/users/all/user_list_all", body)

    async def get_connected_user_count(
        self,
        user_type: str = "agent",
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get count of connected users.

        Args:
            user_type: Type of users. Valid values are: agent, branch, agentless, eb.
                       Note: "all" and "other" are not valid for this endpoint and
                       will result in a 400 error from the API.
            hours: Number of hours to look back
            filters: Additional filter rules
        """
        body = self._build_query_body(hours, filters)
        return await self._post(f"query/users/{user_type}/connected_user_count", body)

    async def get_applications(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get list of internal applications."""
        body = self._build_query_body(hours, filters)
        return await self._post("query/applications/internal/application_list", body)

    async def get_site_count(
        self,
        hours: int = 24,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Get count of sites."""
        body = self._build_query_body(hours, filters)
        return await self._post("query/sites/site_count", body)

    def _build_query_body(
        self,
        hours: int,
        filters: Optional[list[FilterRule]] = None,
    ) -> dict[str, Any]:
        """Build a query request body."""
        rules = [
            {
                "property": "event_time",
                "operator": "last_n_hours",
                "values": [hours],
            }
        ]

        if filters:
            for f in filters:
                rules.append({
                    "property": f.property,
                    "operator": f.operator.value if isinstance(f.operator, Operator) else f.operator,
                    "values": f.values,
                })

        return {"filter": {"rules": rules}}

    def filter(
        self,
        property: str,
        operator: Operator,
        values: list[Any],
    ) -> FilterRule:
        """Create a filter rule for queries."""
        return FilterRule(property=property, operator=operator, values=values)
