"""
Authentication client for Prisma Access Insights API.

Uses OAuth2 client credentials flow with the same auth mechanism as SCM.
"""

import time
import logging
from dataclasses import dataclass
from typing import Optional

import httpx


logger = logging.getLogger(__name__)


# Default timeout configuration
DEFAULT_CONNECT_TIMEOUT = 10.0  # seconds for connection establishment
DEFAULT_READ_TIMEOUT = 30.0  # seconds for reading response
DEFAULT_WRITE_TIMEOUT = 30.0  # seconds for writing request

# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF = 1.0  # Initial backoff in seconds (doubles each retry)

# Retryable exceptions and status codes
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass
class TokenResponse:
    """OAuth2 token response."""
    access_token: str
    token_type: str
    expires_in: int
    scope: str


class AuthClient:
    """OAuth2 authentication client for Prisma Access APIs."""

    DEFAULT_AUTH_URL = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tsg_id: str,
        auth_url: Optional[str] = None,
        timeout: Optional[httpx.Timeout] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
    ):
        """Initialize the auth client.

        Args:
            client_id: OAuth2 client ID (service account email)
            client_secret: OAuth2 client secret
            tsg_id: Tenant Service Group ID
            auth_url: Optional custom auth URL
            timeout: Optional httpx.Timeout configuration
            max_retries: Maximum number of retry attempts (default: 3)
            retry_backoff: Initial retry backoff in seconds (default: 1.0)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tsg_id = tsg_id
        self.auth_url = auth_url or self.DEFAULT_AUTH_URL
        self.timeout = timeout or httpx.Timeout(
            connect=DEFAULT_CONNECT_TIMEOUT,
            read=DEFAULT_READ_TIMEOUT,
            write=DEFAULT_WRITE_TIMEOUT,
            pool=DEFAULT_READ_TIMEOUT,
        )
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        self._access_token: Optional[str] = None
        self._token_expiry: float = 0

    @property
    def is_token_valid(self) -> bool:
        """Check if the current token is still valid."""
        if not self._access_token:
            return False
        # Add 60 second buffer before expiry
        return time.time() < (self._token_expiry - 60)

    def get_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token string.

        Raises:
            httpx.HTTPError: If token request fails.
        """
        if self.is_token_valid:
            return self._access_token

        return self._refresh_token()

    def _refresh_token(self) -> str:
        """Fetch a new access token from the auth server.

        Returns:
            New access token string.

        Raises:
            httpx.HTTPError: If token request fails after all retries.
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.auth_url,
                        data={
                            "grant_type": "client_credentials",
                            "scope": f"tsg_id:{self.tsg_id}",
                        },
                        auth=(self.client_id, self.client_secret),
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )

                    # Check for retryable status codes
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        if attempt < self.max_retries:
                            backoff = self.retry_backoff * (2 ** attempt)
                            logger.warning(
                                f"Auth request failed with status {response.status_code}, "
                                f"retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})"
                            )
                            time.sleep(backoff)
                            continue

                    response.raise_for_status()

                    data = response.json()
                    token_response = TokenResponse(
                        access_token=data["access_token"],
                        token_type=data.get("token_type", "Bearer"),
                        expires_in=data.get("expires_in", 900),
                        scope=data.get("scope", ""),
                    )

                    self._access_token = token_response.access_token
                    self._token_expiry = time.time() + token_response.expires_in

                    return self._access_token

            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                if attempt < self.max_retries:
                    backoff = self.retry_backoff * (2 ** attempt)
                    logger.warning(
                        f"Auth request failed with {type(e).__name__}: {e}, "
                        f"retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(backoff)
                else:
                    logger.error(
                        f"Auth request failed after {self.max_retries + 1} attempts: {e}"
                    )
                    raise

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Token refresh failed unexpectedly")

    def invalidate_token(self) -> None:
        """Invalidate the current token, forcing a refresh on next request."""
        self._access_token = None
        self._token_expiry = 0


class AsyncAuthClient:
    """Async OAuth2 authentication client for Prisma Access APIs."""

    DEFAULT_AUTH_URL = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tsg_id: str,
        auth_url: Optional[str] = None,
        timeout: Optional[httpx.Timeout] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
    ):
        """Initialize the async auth client.

        Args:
            client_id: OAuth2 client ID (service account email)
            client_secret: OAuth2 client secret
            tsg_id: Tenant Service Group ID
            auth_url: Optional custom auth URL
            timeout: Optional httpx.Timeout configuration
            max_retries: Maximum number of retry attempts (default: 3)
            retry_backoff: Initial retry backoff in seconds (default: 1.0)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tsg_id = tsg_id
        self.auth_url = auth_url or self.DEFAULT_AUTH_URL
        self.timeout = timeout or httpx.Timeout(
            connect=DEFAULT_CONNECT_TIMEOUT,
            read=DEFAULT_READ_TIMEOUT,
            write=DEFAULT_WRITE_TIMEOUT,
            pool=DEFAULT_READ_TIMEOUT,
        )
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        self._access_token: Optional[str] = None
        self._token_expiry: float = 0

    @property
    def is_token_valid(self) -> bool:
        """Check if the current token is still valid."""
        if not self._access_token:
            return False
        return time.time() < (self._token_expiry - 60)

    async def get_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        if self.is_token_valid:
            return self._access_token

        return await self._refresh_token()

    async def _refresh_token(self) -> str:
        """Fetch a new access token from the auth server.

        Returns:
            New access token string.

        Raises:
            httpx.HTTPError: If token request fails after all retries.
        """
        import asyncio

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.auth_url,
                        data={
                            "grant_type": "client_credentials",
                            "scope": f"tsg_id:{self.tsg_id}",
                        },
                        auth=(self.client_id, self.client_secret),
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )

                    # Check for retryable status codes
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        if attempt < self.max_retries:
                            backoff = self.retry_backoff * (2 ** attempt)
                            logger.warning(
                                f"Async auth request failed with status {response.status_code}, "
                                f"retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})"
                            )
                            await asyncio.sleep(backoff)
                            continue

                    response.raise_for_status()

                    data = response.json()
                    self._access_token = data["access_token"]
                    self._token_expiry = time.time() + data.get("expires_in", 900)

                    return self._access_token

            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                if attempt < self.max_retries:
                    backoff = self.retry_backoff * (2 ** attempt)
                    logger.warning(
                        f"Async auth request failed with {type(e).__name__}: {e}, "
                        f"retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        f"Async auth request failed after {self.max_retries + 1} attempts: {e}"
                    )
                    raise

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Token refresh failed unexpectedly")

    def invalidate_token(self) -> None:
        """Invalidate the current token."""
        self._access_token = None
        self._token_expiry = 0
