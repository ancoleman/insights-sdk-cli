#!/usr/bin/env python3
"""
CLI for Prisma Access Insights SDK.

Provides command-line access to query insights data with organized subcommands.

Command Groups:
- users: User queries (list, count, sessions, devices, risky, active, histogram)
- apps: Application queries (list, info, risk, tags, transfer)
- accelerated: Accelerated application metrics
- sites: Site queries (list, traffic, bandwidth, search)
- security: PAB security events (access, data)
- monitoring: Monitored user metrics (users, devices, experience)
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Annotated
from enum import Enum

import httpx
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.json import JSON

from .client import InsightsClient
from .models import Region, Operator, FilterRule


# Configure logging for verbose mode
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.WARNING,
)
logger = logging.getLogger(__name__)

# Load .env file from current directory or home directory
load_dotenv()
load_dotenv(Path.home() / ".insights-sdk" / ".env")


def handle_api_error(e: Exception, console: Console) -> None:
    """Handle API errors with informative messages.

    Args:
        e: The exception that was raised
        console: Rich console for output
    """
    if isinstance(e, httpx.HTTPStatusError):
        status_code = e.response.status_code
        if status_code == 400:
            console.print(f"[red]Error 400 (Bad Request): Invalid filter or query parameters[/red]")
            console.print("[yellow]Check that required filters are provided for this endpoint[/yellow]")
            try:
                error_detail = e.response.json()
                console.print(f"[dim]API response: {json.dumps(error_detail, indent=2)}[/dim]")
            except Exception:
                console.print(f"[dim]Response: {e.response.text[:500]}[/dim]")
        elif status_code == 401:
            console.print(f"[red]Error 401 (Unauthorized): Invalid or expired credentials[/red]")
            console.print("[yellow]Check your SCM_CLIENT_ID and SCM_CLIENT_SECRET[/yellow]")
        elif status_code == 403:
            console.print(f"[red]Error 403 (Forbidden): Insufficient permissions[/red]")
            console.print("[yellow]Check that your service account has access to this TSG[/yellow]")
            console.print("[yellow]Verify SCM_TSG_ID is correct[/yellow]")
        elif status_code == 404:
            console.print(f"[red]Error 404 (Not Found): Endpoint or resource not found[/red]")
        elif status_code == 429:
            console.print(f"[red]Error 429 (Rate Limited): Too many requests[/red]")
            console.print("[yellow]Wait a moment and try again[/yellow]")
        elif status_code >= 500:
            console.print(f"[red]Error {status_code} (Server Error): API server error[/red]")
            console.print("[yellow]This is a temporary issue. Please retry.[/yellow]")
        else:
            console.print(f"[red]Error {status_code}: {e}[/red]")
    elif isinstance(e, httpx.ConnectTimeout):
        console.print(f"[red]Connection Timeout: Could not establish connection[/red]")
        console.print("[yellow]Check your network connection and try again[/yellow]")
        console.print("[dim]The request will automatically retry up to 3 times[/dim]")
    elif isinstance(e, httpx.ReadTimeout):
        console.print(f"[red]Read Timeout: Server took too long to respond[/red]")
        console.print("[yellow]The API may be slow. Try again or use --hours with a smaller value.[/yellow]")
    elif isinstance(e, (httpx.ConnectError, httpx.RemoteProtocolError)):
        console.print(f"[red]Network Error: {type(e).__name__}[/red]")
        console.print("[yellow]Check your network connection and try again[/yellow]")
        console.print(f"[dim]Details: {e}[/dim]")
    elif "SSL" in str(type(e).__name__) or "ssl" in str(e).lower():
        console.print(f"[red]SSL/TLS Error: Secure connection failed[/red]")
        console.print("[yellow]This may be a network issue. Retrying usually helps.[/yellow]")
        console.print(f"[dim]Details: {e}[/dim]")
    else:
        handle_api_error(e, console)

console = Console()


# ═══════════════════════════════════════════════════════════════════
# Enums for CLI arguments
# ═══════════════════════════════════════════════════════════════════

class UserType(str, Enum):
    agent = "agent"
    branch = "branch"
    agentless = "agentless"
    eb = "eb"
    other = "other"
    all = "all"


class HistogramMetric(str, Enum):
    throughput = "throughput"
    packet_loss = "packet-loss"
    rtt = "rtt"
    boost = "boost"


# ═══════════════════════════════════════════════════════════════════
# Common Options (defined as functions for reuse)
# ═══════════════════════════════════════════════════════════════════

def client_id_option() -> Optional[str]:
    return typer.Option(None, "--client-id", "-c", help="OAuth2 client ID", envvar="SCM_CLIENT_ID")

def client_secret_option() -> Optional[str]:
    return typer.Option(None, "--client-secret", "-s", help="OAuth2 client secret", envvar="SCM_CLIENT_SECRET")

def tsg_id_option() -> Optional[str]:
    return typer.Option(None, "--tsg-id", "-t", help="Tenant Service Group ID", envvar="SCM_TSG_ID")

def region_option() -> str:
    return typer.Option("americas", "--region", "-r", help="API region (americas, europe, asia, apac)")

def hours_option() -> int:
    return typer.Option(24, "--hours", "-H", help="Hours to look back")

def json_option() -> bool:
    return typer.Option(False, "--json", "-j", help="Output raw JSON")

def limit_option() -> int:
    return typer.Option(10, "--limit", "-l", help="Limit number of results displayed")


# ═══════════════════════════════════════════════════════════════════
# Client Factory
# ═══════════════════════════════════════════════════════════════════

def get_client(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    tsg_id: Optional[str] = None,
    region: str = "americas",
) -> InsightsClient:
    """Create an InsightsClient from provided or environment credentials."""
    client_id = client_id or os.environ.get("SCM_CLIENT_ID") or os.environ.get("INSIGHTS_CLIENT_ID")
    client_secret = client_secret or os.environ.get("SCM_CLIENT_SECRET") or os.environ.get("INSIGHTS_CLIENT_SECRET")
    tsg_id = tsg_id or os.environ.get("SCM_TSG_ID") or os.environ.get("INSIGHTS_TSG_ID")

    if not all([client_id, client_secret, tsg_id]):
        console.print("[red]Error: Missing credentials[/red]")
        console.print("Set SCM_CLIENT_ID, SCM_CLIENT_SECRET, SCM_TSG_ID environment variables")
        console.print("Or use --client-id, --client-secret, --tsg-id options")
        raise typer.Exit(code=1)

    region_enum = Region(region.lower())
    return InsightsClient(
        client_id=client_id,
        client_secret=client_secret,
        tsg_id=tsg_id,
        region=region_enum,
    )


# ═══════════════════════════════════════════════════════════════════
# Main App and Subcommand Groups
# ═══════════════════════════════════════════════════════════════════

app = typer.Typer(
    name="insights",
    help="Query Prisma Access Insights 3.0 API",
    add_completion=False,
    no_args_is_help=True,
)


@app.callback()
def main_callback(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose logging (shows retry attempts)")] = False,
):
    """Query Prisma Access Insights 3.0 API with automatic retry and error handling."""
    if verbose:
        logging.getLogger("insights_sdk").setLevel(logging.DEBUG)
        logging.getLogger("insights_sdk.auth").setLevel(logging.DEBUG)
        logging.getLogger("insights_sdk.client").setLevel(logging.DEBUG)
        # Set root logger to INFO to avoid too much httpx noise
        logging.getLogger().setLevel(logging.INFO)

# Subcommand groups
users_app = typer.Typer(help="User queries (list, count, sessions, devices, risky, active)")
apps_app = typer.Typer(help="Application queries (list, info, risk, tags, transfer)")
accelerated_app = typer.Typer(help="Accelerated application metrics")
sites_app = typer.Typer(help="Site queries (list, traffic, bandwidth, search)")
security_app = typer.Typer(help="PAB security events (access, data)")
monitoring_app = typer.Typer(help="Monitored user metrics (users, devices, experience)")

app.add_typer(users_app, name="users")
app.add_typer(apps_app, name="apps")
app.add_typer(accelerated_app, name="accelerated")
app.add_typer(sites_app, name="sites")
app.add_typer(security_app, name="security")
app.add_typer(monitoring_app, name="monitoring")


# ═══════════════════════════════════════════════════════════════════
# USERS Commands
# ═══════════════════════════════════════════════════════════════════

@users_app.command("list")
def users_list(
    user_type: Annotated[UserType, typer.Argument(help="User type")] = UserType.agent,
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c", help="OAuth2 client ID")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s", help="OAuth2 client secret")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t", help="Tenant Service Group ID")] = None,
    region: Annotated[str, typer.Option("--region", "-r", help="API region")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H", help="Hours to look back")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j", help="Output raw JSON")] = False,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Limit results")] = 10,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Platform type filter (prisma_access, ngfw)")] = None,
):
    """List users by type (agent, branch, agentless, eb, other, all)."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            endpoint_map = {
                UserType.agent: "query/users/agent/user_list",
                UserType.branch: "query/users/branch/user_list",
                UserType.agentless: "query/users/agentless/users",
                UserType.eb: "query/users/eb/user_list",
                UserType.other: "query/users/other/user_list",
                UserType.all: "query/users/all/user_list_all",
            }

            # Agent endpoints require platform_type filter
            filters = None
            if user_type == UserType.agent:
                platform_val = platform or "prisma_access"
                filters = [FilterRule(property="platform_type", operator=Operator.IN, values=[platform_val])]
            elif platform:
                filters = [FilterRule(property="platform_type", operator=Operator.IN, values=[platform])]

            body = client._build_query_body(hours, filters)
            result = client._post(endpoint_map[user_type], body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                _display_users(result, limit, user_type.value)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@users_app.command("count")
def users_count(
    user_type: Annotated[UserType, typer.Argument(help="User type")] = UserType.agent,
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    current: Annotated[bool, typer.Option("--current", help="Get current count (agent only)")] = False,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Platform type (prisma_access, ngfw)")] = None,
):
    """Get connected user count by type."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            if current and user_type == UserType.agent:
                endpoint = "query/users/agent/current_connected_user_count"
            else:
                endpoint = f"query/users/{user_type.value}/connected_user_count"

            # Agent endpoints require platform_type filter
            filters = None
            if user_type == UserType.agent and current:
                platform_val = platform or "prisma_access"
                filters = [FilterRule(property="platform_type", operator=Operator.IN, values=[platform_val])]

            body = client._build_query_body(hours, filters)
            result = client._post(endpoint, body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                data = result.get("data", [])
                if isinstance(data, list) and len(data) > 0:
                    count = data[0].get("user_count", data[0].get("count", "N/A"))
                else:
                    count = "N/A"
                label = "Current" if current else "Connected"
                console.print(f"[green]{label} {user_type.value} users (last {hours}h):[/green] {count}")
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@users_app.command("sessions")
def users_sessions(
    user_type: Annotated[UserType, typer.Argument(help="User type (agent requires --username)")] = UserType.other,
    username: Annotated[Optional[str], typer.Option("--username", "-u", help="Username filter (required for agent)")] = None,
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    limit: Annotated[int, typer.Option("--limit", "-l")] = 10,
):
    """List user sessions by type."""
    if user_type == UserType.agent and not username:
        console.print("[red]Error: --username is required for agent sessions[/red]")
        raise typer.Exit(code=1)

    if user_type in [UserType.eb, UserType.all]:
        console.print(f"[red]Error: session_list not available for {user_type.value}[/red]")
        raise typer.Exit(code=1)

    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            endpoint = f"query/users/{user_type.value}/session_list"

            filters = None
            if username:
                filters = [FilterRule(property="username", operator=Operator.IN, values=[username])]

            body = client._build_query_body(hours, filters)
            result = client._post(endpoint, body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                _display_sessions(result, limit)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@users_app.command("devices")
def users_devices(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    limit: Annotated[int, typer.Option("--limit", "-l")] = 10,
    unique: Annotated[bool, typer.Option("--unique", help="Show unique device connections")] = False,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Platform type (prisma_access, ngfw)")] = None,
):
    """List agent devices."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            endpoint = "query/users/agent/unique_device_connections_list" if unique else "query/users/agent/device_list"
            # Agent endpoints require platform_type filter
            platform_val = platform or "prisma_access"
            filters = [FilterRule(property="platform_type", operator=Operator.IN, values=[platform_val])]
            body = client._build_query_body(hours, filters)
            result = client._post(endpoint, body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                _display_devices(result, limit)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@users_app.command("risky")
def users_risky(
    user_type: Annotated[UserType, typer.Argument(help="User type")] = UserType.agent,
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Platform type (prisma_access, ngfw)")] = None,
):
    """Get risky user count by type."""
    if user_type in [UserType.eb, UserType.all]:
        console.print(f"[red]Error: risky_user_count not available for {user_type.value}[/red]")
        raise typer.Exit(code=1)

    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            # Risky user count endpoint - available for agent, agentless, branch, other
            if user_type == UserType.agent:
                endpoint = "query/users/agent/risky_user_count"
            elif user_type in [UserType.agentless, UserType.branch, UserType.other]:
                endpoint = f"query/{user_type.value}/risky_user_count"
            else:
                console.print(f"[red]Error: risky_user_count not available for {user_type.value}[/red]")
                raise typer.Exit(code=1)

            # Agent endpoints require platform_type filter
            filters = None
            if user_type == UserType.agent:
                platform_val = platform or "prisma_access"
                filters = [FilterRule(property="platform_type", operator=Operator.IN, values=[platform_val])]

            body = client._build_query_body(hours, filters)
            result = client._post(endpoint, body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                _display_count(result, f"Risky {user_type.value} users", hours)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@users_app.command("active")
def users_active(
    user_type: Annotated[UserType, typer.Argument(help="User type")] = UserType.agentless,
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    show_list: Annotated[bool, typer.Option("--list", help="Show active user list instead of count")] = False,
    limit: Annotated[int, typer.Option("--limit", "-l")] = 10,
):
    """Get active user count or list (agentless, branch, eb, other)."""
    if user_type in [UserType.agent, UserType.all]:
        console.print(f"[red]Error: active_user_count not available for {user_type.value}[/red]")
        raise typer.Exit(code=1)

    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            action = "active_user_list" if show_list else "active_user_count"
            endpoint = f"query/users/{user_type.value}/{action}"
            body = client._build_query_body(hours, None)
            result = client._post(endpoint, body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            elif show_list:
                _display_users(result, limit, user_type.value)
            else:
                _display_count(result, f"Active {user_type.value} users", hours)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@users_app.command("histogram")
def users_histogram(
    user_type: Annotated[UserType, typer.Argument(help="User type")] = UserType.agent,
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    devices: Annotated[bool, typer.Option("--devices", help="Device count histogram (agent only)")] = False,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Platform type (prisma_access, ngfw)")] = None,
    interval: Annotated[int, typer.Option("--interval", "-i", help="Histogram interval in minutes")] = 30,
):
    """Get user count histogram over time."""
    if user_type == UserType.all:
        console.print(f"[red]Error: histogram not available for {user_type.value}[/red]")
        raise typer.Exit(code=1)

    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            if devices and user_type == UserType.agent:
                endpoint = "query/users/agent/connected_user_device_count_histogram"
            elif user_type == UserType.agent:
                endpoint = "query/users/agent/connected_user_count_histogram"
            else:
                endpoint = f"query/users/{user_type.value}/user_count_histogram"

            # Agent endpoints require platform_type filter
            filters = None
            if user_type == UserType.agent:
                platform_val = platform or "prisma_access"
                filters = [FilterRule(property="platform_type", operator=Operator.IN, values=[platform_val])]

            body = client._build_query_body(hours, filters)
            # Histogram endpoints require histogram configuration
            body["histogram"] = {
                "enableEmptyInterval": True,
                "property": "event_time",
                "range": "minute",
                "value": interval,
            }
            result = client._post(endpoint, body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                _display_histogram(result, f"{user_type.value} user count")
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@users_app.command("entities")
def users_entities(
    user_type: Annotated[UserType, typer.Argument(help="User type")] = UserType.agent,
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Platform type (prisma_access, ngfw)")] = None,
):
    """Get connected entity count (agent, branch, other)."""
    if user_type not in [UserType.agent, UserType.branch, UserType.other]:
        console.print(f"[red]Error: entity_count only available for agent, branch, other[/red]")
        raise typer.Exit(code=1)

    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            endpoint = f"query/users/{user_type.value}/connected_entity_count"

            # Agent endpoints require platform_type filter
            filters = None
            if user_type == UserType.agent:
                platform_val = platform or "prisma_access"
                filters = [FilterRule(property="platform_type", operator=Operator.IN, values=[platform_val])]

            body = client._build_query_body(hours, filters)
            result = client._post(endpoint, body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                _display_count(result, f"Connected {user_type.value} entities", hours)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@users_app.command("versions")
def users_versions(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Platform type (prisma_access, ngfw)")] = None,
):
    """Get agent client version distribution."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            endpoint = "query/users/agent/client_version_distribution"
            # This endpoint requires client_agent_type filter
            platform_val = platform or "prisma_access"
            filters = [
                FilterRule(property="client_agent_type", operator=Operator.IN, values=["traped"]),
                FilterRule(property="platform_type", operator=Operator.IN, values=[platform_val]),
            ]
            body = client._build_query_body(hours, filters)
            result = client._post(endpoint, body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                _display_distribution(result, "Agent Version Distribution")
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


# ═══════════════════════════════════════════════════════════════════
# APPS Commands
# ═══════════════════════════════════════════════════════════════════

@apps_app.command("list")
def apps_list(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    limit: Annotated[int, typer.Option("--limit", "-l")] = 10,
):
    """List internal applications."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            result = client._post("query/applications/internal/application_list", body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                _display_applications(result, limit)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@apps_app.command("info")
def apps_info(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
):
    """Get application information."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            result = client._post("query/applications/app_info", body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@apps_app.command("risk")
def apps_risk(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
):
    """Get applications grouped by risk score."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            result = client._post("query/applications/internal/app_by_risk_score", body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                _display_risk_breakdown(result)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@apps_app.command("tags")
def apps_tags(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
):
    """Get applications grouped by tag."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            result = client._post("query/applications/internal/app_by_tag", body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@apps_app.command("transfer")
def apps_transfer(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    by_destination: Annotated[bool, typer.Option("--by-destination", help="Group by destination")] = False,
):
    """Get data transfer by application."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            endpoint = "query/applications/internal/total_data_transfer_by_destination" if by_destination else "query/applications/internal/total_data_transfer_application"
            body = client._build_query_body(hours, None)
            result = client._post(endpoint, body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@apps_app.command("bandwidth")
def apps_bandwidth(
    app_name: Annotated[str, typer.Argument(help="Application name (e.g., 'Zoom', 'Slack')")],
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    interval: Annotated[int, typer.Option("--interval", "-i", help="Histogram interval in minutes")] = 30,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Platform type (prisma_access, ngfw)")] = None,
):
    """Get bandwidth histogram for a specific application.

    Example: insights apps bandwidth Zoom
    """
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            # This endpoint requires an app filter
            filters = [FilterRule(property="app", operator=Operator.IN, values=[app_name])]
            if platform:
                filters.append(FilterRule(property="platform_type", operator=Operator.IN, values=[platform]))

            body = client._build_query_body(hours, filters)
            # Histogram endpoints require histogram configuration
            body["histogram"] = {
                "enableEmptyInterval": True,
                "property": "event_time",
                "range": "minute",
                "value": interval,
            }
            result = client._post("query/app_details_bw_info_histogram", body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


# ═══════════════════════════════════════════════════════════════════
# ACCELERATED Commands
# ═══════════════════════════════════════════════════════════════════

@accelerated_app.command("list")
def accelerated_list(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    limit: Annotated[int, typer.Option("--limit", "-l")] = 10,
):
    """List accelerated applications."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            result = client._post("query/accelerated_applications/accelerated_application_list", body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                _display_applications(result, limit)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@accelerated_app.command("count")
def accelerated_count(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    users: Annotated[bool, typer.Option("--users", help="Count users instead of apps")] = False,
):
    """Get accelerated application or user count."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            endpoint = "query/accelerated_applications/users_count" if users else "query/accelerated_applications/applications_count"
            body = client._build_query_body(hours, None)
            result = client._post(endpoint, body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                label = "Accelerated app users" if users else "Accelerated applications"
                _display_count(result, label, hours)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@accelerated_app.command("performance")
def accelerated_performance(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
):
    """Get performance boost metrics."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            result = client._post("query/accelerated_applications/performance_boost", body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@accelerated_app.command("transfer")
def accelerated_transfer(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    per_app: Annotated[bool, typer.Option("--per-app", help="Show throughput per app")] = False,
):
    """Get data transfer metrics for accelerated apps."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            endpoint = "query/accelerated_applications/data_transfer_throughput_per_app" if per_app else "query/accelerated_applications/total_data_transfer"
            body = client._build_query_body(hours, None)
            result = client._post(endpoint, body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@accelerated_app.command("response-time")
def accelerated_response_time(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    per_app: Annotated[bool, typer.Option("--per-app", help="Show per-app breakdown")] = False,
):
    """Get response time improvement metrics."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            if per_app:
                endpoint = "query/applications/accelerated_applications/response_time_before_and_after_improvement_per_app"
            else:
                endpoint = "query/applications/accelerated_applications/response_time_before_and_after_improvement"
            body = client._build_query_body(hours, None)
            result = client._post(endpoint, body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@accelerated_app.command("histogram")
def accelerated_histogram(
    metric: Annotated[HistogramMetric, typer.Argument(help="Metric type")] = HistogramMetric.throughput,
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
):
    """Get histogram for accelerated app metrics (throughput, packet-loss, rtt, boost)."""
    endpoint_map = {
        HistogramMetric.throughput: "query/accelerated_applications/throughput_per_app_histogram",
        HistogramMetric.packet_loss: "query/accelerated_applications/packet_loss_per_app_histogram",
        HistogramMetric.rtt: "query/accelerated_applications/rtt_variance_histogram",
        HistogramMetric.boost: "query/accelerated_applications/accelerated_applications/throughput_before_after_boost_histogram",
    }

    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            result = client._post(endpoint_map[metric], body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


# ═══════════════════════════════════════════════════════════════════
# SITES Commands
# ═══════════════════════════════════════════════════════════════════

@sites_app.command("list")
def sites_list(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
):
    """Get site count by type."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            result = client._post("query/sites/site_count", body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                data = result.get("data", [])
                if isinstance(data, list):
                    total_sites = sum(item.get("site_count", 0) for item in data)
                    console.print(f"[green]Total sites (last {hours}h):[/green] {total_sites}")
                    for item in data:
                        node_type = item.get("node_type", "Unknown")
                        site_count = item.get("site_count", 0)
                        console.print(f"  {node_type}: {site_count} sites")
                else:
                    console.print("[yellow]No site data available[/yellow]")
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@sites_app.command("traffic")
def sites_traffic(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
):
    """Get site traffic information."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            result = client._post("query/sites/site_traffic", body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@sites_app.command("bandwidth")
def sites_bandwidth(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    interval: Annotated[int, typer.Option("--interval", "-i", help="Histogram interval in minutes")] = 30,
):
    """Get site bandwidth consumption histogram."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            # Histogram endpoints require histogram configuration
            body["histogram"] = {
                "enableEmptyInterval": True,
                "property": "event_time",
                "range": "minute",
                "value": interval,
            }
            result = client._post("query/sites/bandwidth_consumption_histogram", body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@sites_app.command("sessions")
def sites_sessions(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    node_type: Annotated[Optional[int], typer.Option("--node-type", "-n", help="Node type filter (e.g., 51)")] = None,
    site_name: Annotated[Optional[str], typer.Option("--site", "-S", help="Site name filter")] = None,
):
    """Get site session count."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            # This endpoint doesn't use event_time filter, uses optional node_type/site_name
            body: dict = {"filter": {"rules": []}}
            if node_type is not None:
                body["filter"]["rules"].append({
                    "property": "node_type",
                    "operator": "in",
                    "values": [node_type],
                })
            if site_name:
                body["filter"]["rules"].append({
                    "property": "site_name",
                    "operator": "in",
                    "values": [site_name],
                })
            result = client._post("query/sites/session_count", body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            else:
                _display_count(result, "Site sessions", 0)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@sites_app.command("search")
def sites_search(
    term: Annotated[str, typer.Argument(help="Search term for site location")],
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
):
    """Search sites by location."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            body["search"] = term
            result = client._post("query/sites/site_location_search_contains", body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


# ═══════════════════════════════════════════════════════════════════
# SECURITY (PAB) Commands
# ═══════════════════════════════════════════════════════════════════

@security_app.command("access")
def security_access(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    blocked: Annotated[bool, typer.Option("--blocked", help="Show blocked events only")] = False,
    breakdown: Annotated[bool, typer.Option("--breakdown", help="Show breakdown")] = False,
    histogram: Annotated[bool, typer.Option("--histogram", help="Show histogram")] = False,
    interval: Annotated[int, typer.Option("--interval", "-i", help="Histogram interval in minutes")] = 30,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Platform type (prisma_access)")] = None,
):
    """Get PAB access events."""
    # Build endpoint based on flags
    if blocked and breakdown and histogram:
        endpoint = "query/pab/access_events_breakdown_blocked_histogram"
    elif blocked and breakdown:
        endpoint = "query/pab/access_events_breakdown_blocked"
    elif blocked and histogram:
        endpoint = "query/pab/access_events_blocked_histogram"
    elif breakdown and histogram:
        endpoint = "query/pab/access_events_breakdown_histogram"
    elif blocked:
        endpoint = "query/pab/access_events_blocked"
    elif breakdown:
        endpoint = "query/applications/pab/access_events_breakdown"
    elif histogram:
        endpoint = "query/pab/access_events_histogram"
    else:
        endpoint = "query/applications/pab/access_events"

    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            # Histogram endpoints require platform_type filter
            filters = None
            if histogram:
                platform_val = platform or "prisma_access"
                filters = [FilterRule(property="platform_type", operator=Operator.IN, values=[platform_val])]
            body = client._build_query_body(hours, filters)
            # Histogram endpoints require histogram configuration
            if histogram:
                body["histogram"] = {
                    "enableEmptyInterval": True,
                    "property": "event_time",
                    "range": "minute",
                    "value": interval,
                }
            result = client._post(endpoint, body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@security_app.command("data")
def security_data(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    blocked: Annotated[bool, typer.Option("--blocked", help="Show blocked events only")] = False,
    breakdown: Annotated[bool, typer.Option("--breakdown", help="Show breakdown")] = False,
    histogram: Annotated[bool, typer.Option("--histogram", help="Show histogram")] = False,
    interval: Annotated[int, typer.Option("--interval", "-i", help="Histogram interval in minutes")] = 30,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Platform type (prisma_access)")] = None,
):
    """Get PAB data events."""
    # Build endpoint based on flags
    if blocked and breakdown and histogram:
        endpoint = "query/pab/data_events_breakdown_blocked_histogram"
    elif blocked and breakdown:
        endpoint = "query/pab/data_events_breakdown_blocked"
    elif blocked and histogram:
        endpoint = "query/pab/data_events_blocked_histogram"
    elif breakdown and histogram:
        endpoint = "query/pab/data_events_breakdown_histogram"
    elif blocked:
        endpoint = "query/pab/data_events_blocked"
    elif breakdown:
        endpoint = "query/pab/data_events_breakdown"
    elif histogram:
        endpoint = "query/pab/data_events_histogram"
    else:
        endpoint = "query/applications/pab/data_events"

    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            # Histogram endpoints require platform_type filter
            filters = None
            if histogram:
                platform_val = platform or "prisma_access"
                filters = [FilterRule(property="platform_type", operator=Operator.IN, values=[platform_val])]
            body = client._build_query_body(hours, filters)
            # Histogram endpoints require histogram configuration
            if histogram:
                body["histogram"] = {
                    "enableEmptyInterval": True,
                    "property": "event_time",
                    "range": "minute",
                    "value": interval,
                }
            result = client._post(endpoint, body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


# ═══════════════════════════════════════════════════════════════════
# MONITORING Commands
# ═══════════════════════════════════════════════════════════════════

@monitoring_app.command("users")
def monitoring_users(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    histogram: Annotated[bool, typer.Option("--histogram", help="Show histogram")] = False,
):
    """Get monitored user count."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            endpoint = "query/user/monitored/user_count_histogram" if histogram else "query/user/monitored/user_count"
            body = client._build_query_body(hours, None)
            result = client._post(endpoint, body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            elif histogram:
                _display_histogram(result, "Monitored user count")
            else:
                _display_count(result, "Monitored users", hours)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@monitoring_app.command("devices")
def monitoring_devices(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    histogram: Annotated[bool, typer.Option("--histogram", help="Show histogram")] = False,
    interval: Annotated[int, typer.Option("--interval", "-i", help="Histogram interval in minutes")] = 30,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Platform type (prisma_access, ngfw)")] = None,
):
    """Get monitored device count."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            endpoint = "query/users/monitored/device_count_histogram" if histogram else "query/users/monitored/device_count"
            # Add platform_type filter if provided
            filters = None
            if platform:
                filters = [FilterRule(property="platform_type", operator=Operator.IN, values=[platform])]
            body = client._build_query_body(hours, filters)
            # Histogram endpoints require histogram configuration
            if histogram:
                body["histogram"] = {
                    "enableEmptyInterval": True,
                    "property": "event_time",
                    "range": "minute",
                    "value": interval,
                }
            result = client._post(endpoint, body)

            if output_json:
                console.print(JSON(json.dumps(result, indent=2, default=str)))
            elif histogram:
                _display_histogram(result, "Monitored device count")
            else:
                _display_count(result, "Monitored devices", hours)
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@monitoring_app.command("experience")
def monitoring_experience(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
):
    """Get user experience scores."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            result = client._post("query/users/monitored/user_experience_score", body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


# ═══════════════════════════════════════════════════════════════════
# UTILITY Commands (on main app)
# ═══════════════════════════════════════════════════════════════════

@app.command("query")
def raw_query(
    endpoint: Annotated[str, typer.Argument(help="API endpoint path (e.g., query/users/agent/user_list)")],
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
    hours: Annotated[int, typer.Option("--hours", "-H")] = 24,
):
    """Execute a raw query against any endpoint (escape hatch)."""
    with get_client(client_id, client_secret, tsg_id, region) as client:
        try:
            body = client._build_query_body(hours, None)
            result = client._post(endpoint, body)
            console.print(JSON(json.dumps(result, indent=2, default=str)))
        except Exception as e:
            handle_api_error(e, console)
            raise typer.Exit(code=1)


@app.command("test")
def test_connection(
    client_id: Annotated[Optional[str], typer.Option("--client-id", "-c")] = None,
    client_secret: Annotated[Optional[str], typer.Option("--client-secret", "-s")] = None,
    tsg_id: Annotated[Optional[str], typer.Option("--tsg-id", "-t")] = None,
    region: Annotated[str, typer.Option("--region", "-r")] = "americas",
):
    """Test API connection and authentication."""
    console.print("[bold]Testing Insights API connection...[/bold]")

    try:
        with get_client(client_id, client_secret, tsg_id, region) as client:
            console.print("  Authenticating...", end=" ")
            token = client._auth.get_token()
            console.print("[green]OK[/green]")
            console.print(f"  Token: {token[:20]}...")

            console.print("  Testing API call...", end=" ")
            body = client._build_query_body(1, None)
            client._post("query/users/agent/connected_user_count", body)
            console.print("[green]OK[/green]")

            console.print(f"\n[green]Connection successful![/green]")
            console.print(f"Region: {region}")
            console.print(f"TSG ID: {client.tsg_id}")

    except Exception as e:
        console.print(f"[red]FAILED[/red]")
        console.print(f"\n[red]Connection failed: {e}[/red]")
        raise typer.Exit(code=1)


# ═══════════════════════════════════════════════════════════════════
# Display Helpers
# ═══════════════════════════════════════════════════════════════════

def _extract_data(result: dict) -> list:
    """Extract data list from API response."""
    data = result.get("data", result.get("items", []))
    if isinstance(data, dict):
        data = data.get("items", data.get("users", data.get("devices", data.get("applications", []))))
    return data if isinstance(data, list) else []


def _display_users(result: dict, limit: int, user_type: str = "agent") -> None:
    """Display user list in a table."""
    data = _extract_data(result)

    if not data:
        console.print("[yellow]No users found[/yellow]")
        return

    table = Table(title=f"{user_type.title()} Users (showing {min(limit, len(data))} of {len(data)})")
    table.add_column("Username", style="cyan")
    table.add_column("Device", style="green")
    table.add_column("Platform")
    table.add_column("Location")
    table.add_column("Version")

    for user in data[:limit]:
        table.add_row(
            str(user.get("username", "N/A")),
            str(user.get("device_name", "N/A")),
            str(user.get("platform_type", "N/A")),
            f"{user.get('source_city', 'N/A')}, {user.get('source_country', 'N/A')}",
            str(user.get("agent_version", user.get("client_version", "N/A"))),
        )

    console.print(table)


def _display_devices(result: dict, limit: int) -> None:
    """Display device list in a table."""
    data = _extract_data(result)

    if not data:
        console.print("[yellow]No devices found[/yellow]")
        return

    table = Table(title=f"Devices (showing {min(limit, len(data))} of {len(data)})")
    table.add_column("Device Name", style="cyan")
    table.add_column("Username", style="green")
    table.add_column("OS")
    table.add_column("Agent Version")

    for device in data[:limit]:
        table.add_row(
            str(device.get("device_name", "N/A")),
            str(device.get("username", "N/A")),
            str(device.get("client_os_version", "N/A")),
            str(device.get("agent_version", "N/A")),
        )

    console.print(table)


def _display_sessions(result: dict, limit: int) -> None:
    """Display session list in a table."""
    data = _extract_data(result)

    if not data:
        console.print("[yellow]No sessions found[/yellow]")
        return

    table = Table(title=f"Sessions (showing {min(limit, len(data))} of {len(data)})")
    table.add_column("Username", style="cyan")
    table.add_column("Device", style="green")
    table.add_column("Source IP")
    table.add_column("Location")
    table.add_column("Status")

    for session in data[:limit]:
        table.add_row(
            str(session.get("username", "N/A")),
            str(session.get("device_name", "N/A")),
            str(session.get("source_ip", "N/A")),
            str(session.get("edge_location_display_name", "N/A")),
            str(session.get("status", "N/A")),
        )

    console.print(table)


def _display_applications(result: dict, limit: int) -> None:
    """Display application list in a table."""
    data = _extract_data(result)

    if not data:
        console.print("[yellow]No applications found[/yellow]")
        return

    table = Table(title=f"Applications (showing {min(limit, len(data))} of {len(data)})")
    table.add_column("Name", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Risk", justify="right")
    table.add_column("Sessions", justify="right")
    table.add_column("Data Transfer", justify="right")

    for app in data[:limit]:
        risk = app.get("risk_score", app.get("risk", "N/A"))
        try:
            risk_val = int(risk) if risk != "N/A" else 0
            risk_style = "red" if risk_val >= 4 else "yellow" if risk_val >= 2 else "green"
            risk_display = f"[{risk_style}]{risk}[/{risk_style}]"
        except (ValueError, TypeError):
            risk_display = str(risk)

        table.add_row(
            str(app.get("app_name", app.get("name", "N/A"))),
            str(app.get("app_category", app.get("category", "N/A"))),
            risk_display,
            str(app.get("sessions", "N/A")),
            _format_bytes(app.get("bytes_sent", 0) + app.get("bytes_received", 0)),
        )

    console.print(table)


def _display_count(result: dict, label: str, hours: int) -> None:
    """Display a count value."""
    data = result.get("data", [])
    if isinstance(data, list) and len(data) > 0:
        # Try common count field names
        count = data[0].get("user_count",
                data[0].get("count",
                data[0].get("device_count",
                data[0].get("session_count",
                data[0].get("entity_count", "N/A")))))
    else:
        count = "N/A"
    console.print(f"[green]{label} (last {hours}h):[/green] {count}")


def _display_risk_breakdown(result: dict) -> None:
    """Display risk score breakdown."""
    data = result.get("data", result)

    table = Table(title="Applications by Risk Score")
    table.add_column("Risk Level", style="bold")
    table.add_column("Count", justify="right")

    if isinstance(data, list):
        for item in data:
            risk = item.get("risk_score", item.get("risk", "Unknown"))
            count = item.get("count", item.get("app_count", 0))
            table.add_row(str(risk), str(count))
    elif isinstance(data, dict):
        for risk, count in data.items():
            table.add_row(str(risk), str(count))

    console.print(table)


def _display_histogram(result: dict, title: str) -> None:
    """Display histogram data."""
    data = result.get("data", [])

    if not data:
        console.print("[yellow]No histogram data available[/yellow]")
        return

    table = Table(title=title)
    table.add_column("Time", style="cyan")
    table.add_column("Value", justify="right")

    for item in data[:20]:  # Limit to 20 rows
        time_val = item.get("timestamp", item.get("time", item.get("event_time", "N/A")))
        count = item.get("count", item.get("value", item.get("user_count", "N/A")))
        table.add_row(str(time_val), str(count))

    console.print(table)


def _display_distribution(result: dict, title: str) -> None:
    """Display distribution data."""
    data = result.get("data", [])

    if not data:
        console.print("[yellow]No distribution data available[/yellow]")
        return

    table = Table(title=title)
    table.add_column("Version", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Percentage", justify="right")

    total = sum(item.get("count", 0) for item in data)
    for item in data:
        version = item.get("version", item.get("client_version", item.get("agent_version", "N/A")))
        count = item.get("count", 0)
        pct = f"{(count / total * 100):.1f}%" if total > 0 else "0%"
        table.add_row(str(version), str(count), pct)

    console.print(table)


def _format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable string."""
    if not bytes_val:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


if __name__ == "__main__":
    app()
