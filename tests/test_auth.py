"""
Unit tests for insights_sdk.auth module.

Tests OAuth2 authentication flow, token management, and caching.
"""

import time
import pytest
import httpx
import respx

from insights_sdk.auth import AuthClient, AsyncAuthClient, TokenResponse

from .conftest import (
    TEST_CLIENT_ID,
    TEST_CLIENT_SECRET,
    TEST_TSG_ID,
    TEST_AUTH_URL,
    TEST_ACCESS_TOKEN,
)


class TestTokenResponse:
    """Tests for TokenResponse dataclass."""

    def test_create_token_response(self):
        """Test creating a token response."""
        token = TokenResponse(
            access_token="test-token",
            token_type="Bearer",
            expires_in=900,
            scope="tsg_id:123",
        )
        assert token.access_token == "test-token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 900
        assert token.scope == "tsg_id:123"


class TestAuthClient:
    """Tests for synchronous AuthClient."""

    def test_init(self):
        """Test AuthClient initialization."""
        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        assert client.client_id == TEST_CLIENT_ID
        assert client.client_secret == TEST_CLIENT_SECRET
        assert client.tsg_id == TEST_TSG_ID
        assert client.auth_url == AuthClient.DEFAULT_AUTH_URL

    def test_init_custom_auth_url(self):
        """Test AuthClient with custom auth URL."""
        custom_url = "https://custom.auth.example.com/token"
        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            auth_url=custom_url,
        )
        assert client.auth_url == custom_url

    def test_is_token_valid_no_token(self):
        """Test token validity when no token exists."""
        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        assert client.is_token_valid is False

    def test_is_token_valid_expired(self):
        """Test token validity when token is expired."""
        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        client._access_token = "test-token"
        client._token_expiry = time.time() - 100  # Expired 100 seconds ago
        assert client.is_token_valid is False

    def test_is_token_valid_within_buffer(self):
        """Test token validity within 60-second buffer."""
        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        client._access_token = "test-token"
        client._token_expiry = time.time() + 30  # Expires in 30 seconds (within buffer)
        assert client.is_token_valid is False

    def test_is_token_valid_fresh(self):
        """Test token validity when token is fresh."""
        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        client._access_token = "test-token"
        client._token_expiry = time.time() + 500  # Expires in 500 seconds
        assert client.is_token_valid is True

    @respx.mock
    def test_get_token_fetches_new_token(self, sample_auth_response):
        """Test that get_token fetches a new token when needed."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )

        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        token = client.get_token()

        assert token == TEST_ACCESS_TOKEN
        assert client._access_token == TEST_ACCESS_TOKEN
        assert client._token_expiry > time.time()

    @respx.mock
    def test_get_token_uses_cached_token(self, sample_auth_response):
        """Test that get_token uses cached token when valid."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )

        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )

        # First call - should fetch token
        token1 = client.get_token()
        assert respx.calls.call_count == 1

        # Second call - should use cached token
        token2 = client.get_token()
        assert respx.calls.call_count == 1  # No additional call
        assert token1 == token2

    @respx.mock
    def test_get_token_refreshes_expired(self, sample_auth_response):
        """Test that get_token refreshes expired token."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )

        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )

        # Set expired token
        client._access_token = "old-token"
        client._token_expiry = time.time() - 100

        token = client.get_token()
        assert token == TEST_ACCESS_TOKEN
        assert respx.calls.call_count == 1

    @respx.mock
    def test_refresh_token_sends_correct_request(self, sample_auth_response):
        """Test that refresh token sends correct auth request."""
        route = respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )

        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        client._refresh_token()

        # Verify request was made
        assert route.called
        request = route.calls[0].request

        # Check content type
        assert "application/x-www-form-urlencoded" in request.headers.get("content-type", "")

    @respx.mock
    def test_refresh_token_handles_error(self):
        """Test that refresh token raises on HTTP error."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(401, json={"error": "invalid_client"})
        )

        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )

        with pytest.raises(httpx.HTTPStatusError):
            client._refresh_token()

    def test_invalidate_token(self):
        """Test invalidating the cached token."""
        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        client._access_token = "test-token"
        client._token_expiry = time.time() + 500

        client.invalidate_token()

        assert client._access_token is None
        assert client._token_expiry == 0
        assert client.is_token_valid is False


class TestAsyncAuthClient:
    """Tests for asynchronous AsyncAuthClient."""

    def test_init(self):
        """Test AsyncAuthClient initialization."""
        client = AsyncAuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        assert client.client_id == TEST_CLIENT_ID
        assert client.client_secret == TEST_CLIENT_SECRET
        assert client.tsg_id == TEST_TSG_ID

    def test_is_token_valid_no_token(self):
        """Test token validity when no token exists."""
        client = AsyncAuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        assert client.is_token_valid is False

    def test_is_token_valid_fresh(self):
        """Test token validity when token is fresh."""
        client = AsyncAuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        client._access_token = "test-token"
        client._token_expiry = time.time() + 500
        assert client.is_token_valid is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_token_async(self, sample_auth_response):
        """Test async get_token fetches new token."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )

        client = AsyncAuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        token = await client.get_token()

        assert token == TEST_ACCESS_TOKEN
        assert client._access_token == TEST_ACCESS_TOKEN

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_token_uses_cached_async(self, sample_auth_response):
        """Test async get_token uses cached token."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_auth_response)
        )

        client = AsyncAuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )

        # First call
        token1 = await client.get_token()
        assert respx.calls.call_count == 1

        # Second call - should use cache
        token2 = await client.get_token()
        assert respx.calls.call_count == 1
        assert token1 == token2

    @pytest.mark.asyncio
    @respx.mock
    async def test_refresh_token_handles_error_async(self):
        """Test async refresh token raises on HTTP error."""
        respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(401, json={"error": "invalid_client"})
        )

        client = AsyncAuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client._refresh_token()

    def test_invalidate_token_async(self):
        """Test invalidating the cached token in async client."""
        client = AsyncAuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        client._access_token = "test-token"
        client._token_expiry = time.time() + 500

        client.invalidate_token()

        assert client._access_token is None
        assert client._token_expiry == 0


class TestAuthClientRetry:
    """Tests for AuthClient retry logic."""

    def test_init_with_custom_retry_settings(self):
        """Test AuthClient initialization with custom retry settings."""
        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            max_retries=5,
            retry_backoff=2.0,
        )
        assert client.max_retries == 5
        assert client.retry_backoff == 2.0

    def test_default_retry_settings(self):
        """Test AuthClient default retry settings."""
        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
        )
        assert client.max_retries == 3
        assert client.retry_backoff == 1.0

    @respx.mock
    def test_retry_on_server_error(self, sample_auth_response):
        """Test that auth retries on 5xx errors."""
        # First two calls return 503, third succeeds
        route = respx.post(TEST_AUTH_URL)
        route.side_effect = [
            httpx.Response(503, json={"error": "service_unavailable"}),
            httpx.Response(503, json={"error": "service_unavailable"}),
            httpx.Response(200, json=sample_auth_response),
        ]

        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            retry_backoff=0.01,  # Fast retries for testing
        )
        token = client.get_token()

        assert token == TEST_ACCESS_TOKEN
        assert route.call_count == 3

    @respx.mock
    def test_retry_exhausted_raises_error(self):
        """Test that auth raises after all retries exhausted."""
        route = respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(503, json={"error": "service_unavailable"})
        )

        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            max_retries=2,
            retry_backoff=0.01,
        )

        with pytest.raises(httpx.HTTPStatusError):
            client._refresh_token()

        # Should have tried 3 times (1 + 2 retries)
        assert route.call_count == 3

    @respx.mock
    def test_no_retry_on_client_error(self):
        """Test that auth doesn't retry on 4xx errors (except 429)."""
        route = respx.post(TEST_AUTH_URL).mock(
            return_value=httpx.Response(401, json={"error": "invalid_client"})
        )

        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            retry_backoff=0.01,
        )

        with pytest.raises(httpx.HTTPStatusError):
            client._refresh_token()

        # Should only try once - 401 is not retryable
        assert route.call_count == 1

    @respx.mock
    def test_retry_on_rate_limit(self, sample_auth_response):
        """Test that auth retries on 429 rate limit."""
        route = respx.post(TEST_AUTH_URL)
        route.side_effect = [
            httpx.Response(429, json={"error": "rate_limited"}),
            httpx.Response(200, json=sample_auth_response),
        ]

        client = AuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            retry_backoff=0.01,
        )
        token = client.get_token()

        assert token == TEST_ACCESS_TOKEN
        assert route.call_count == 2


class TestAsyncAuthClientRetry:
    """Tests for AsyncAuthClient retry logic."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_retry_on_server_error(self, sample_auth_response):
        """Test that async auth retries on 5xx errors."""
        route = respx.post(TEST_AUTH_URL)
        route.side_effect = [
            httpx.Response(502, json={"error": "bad_gateway"}),
            httpx.Response(200, json=sample_auth_response),
        ]

        client = AsyncAuthClient(
            client_id=TEST_CLIENT_ID,
            client_secret=TEST_CLIENT_SECRET,
            tsg_id=TEST_TSG_ID,
            retry_backoff=0.01,
        )
        token = await client.get_token()

        assert token == TEST_ACCESS_TOKEN
        assert route.call_count == 2
