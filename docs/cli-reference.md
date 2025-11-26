# CLI Reference

Complete reference for the Prisma Access Insights CLI.

## Command Structure

The CLI is organized into command groups:

```
insights <group> <command> [options]
```

## Global Options

All commands support these options:

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--client-id` | `-c` | OAuth2 client ID | env: `SCM_CLIENT_ID` |
| `--client-secret` | `-s` | OAuth2 client secret | env: `SCM_CLIENT_SECRET` |
| `--tsg-id` | `-t` | Tenant Service Group ID | env: `SCM_TSG_ID` |
| `--region` | `-r` | API region (americas, europe, asia, apac) | `americas` |
| `--hours` | `-H` | Hours to look back | `24` |
| `--json` | `-j` | Output raw JSON | `false` |
| `--limit` | `-l` | Limit displayed results | `10` |

## Users Commands

Query user data across different connection types.

### `insights users list [TYPE]`

List users by type.

**Arguments:**
- `TYPE`: User type - `agent`, `branch`, `agentless`, `eb`, `other`, `all` (default: `agent`)

**Options:**
- `--platform`, `-p`: Platform type filter (`prisma_access`, `ngfw`) - auto-added for agent

**Examples:**
```bash
insights users list agent              # List agent users
insights users list all --hours 168    # List all users from last 7 days
insights users list other --json       # Output as JSON
insights users list agent --platform ngfw  # Filter by NGFW platform
```

### `insights users count [TYPE]`

Get connected user count.

**Arguments:**
- `TYPE`: User type - `agent`, `branch`, `agentless`, `eb`, `other` (default: `agent`)

**Options:**
- `--current`: Get current count instead of historical (agent only)

**Examples:**
```bash
insights users count agent             # Connected agent users
insights users count agent --current   # Currently connected agent users
insights users count branch --hours 48
```

### `insights users sessions [TYPE]`

List user sessions.

**Arguments:**
- `TYPE`: User type - `agent`, `agentless`, `branch`, `other` (default: `other`)

**Options:**
- `--username`, `-u`: Username filter (required for agent type)

**Examples:**
```bash
insights users sessions                    # List all sessions (other type)
insights users sessions agent -u john.doe  # Agent sessions for specific user
insights users sessions branch --hours 48
```

### `insights users devices`

List agent devices.

**Options:**
- `--unique`: Show unique device connections instead of device list
- `--platform`, `-p`: Platform type filter (`prisma_access`, `ngfw`)

**Examples:**
```bash
insights users devices                 # List agent devices
insights users devices --unique        # Unique device connections
insights users devices --platform ngfw
```

### `insights users risky [TYPE]`

Get risky user count.

**Arguments:**
- `TYPE`: User type - `agent`, `agentless`, `branch`, `other` (default: `agent`)

**Examples:**
```bash
insights users risky agent
insights users risky branch --hours 168
```

### `insights users active [TYPE]`

Get active user count or list (not available for agent/all types).

**Arguments:**
- `TYPE`: User type - `agentless`, `branch`, `eb`, `other` (default: `agentless`)

**Options:**
- `--list`: Show active user list instead of count

**Examples:**
```bash
insights users active agentless        # Active agentless user count
insights users active branch --list    # Active branch user list
```

### `insights users histogram [TYPE]`

Get user count histogram over time.

**Arguments:**
- `TYPE`: User type - `agent`, `branch`, `agentless`, `eb`, `other` (default: `agent`)

**Options:**
- `--devices`: Show device count histogram instead (agent only)

**Examples:**
```bash
insights users histogram agent
insights users histogram agent --devices
insights users histogram branch --hours 168
```

### `insights users entities [TYPE]`

Get connected entity count.

**Arguments:**
- `TYPE`: User type - `agent`, `branch`, `other` (default: `agent`)

**Examples:**
```bash
insights users entities agent
insights users entities branch
```

### `insights users versions`

Get agent client version distribution.

**Examples:**
```bash
insights users versions
insights users versions --hours 168
```

---

## Apps Commands

Query application data.

### `insights apps list`

List internal applications.

**Examples:**
```bash
insights apps list
insights apps list --hours 168 --limit 50
```

### `insights apps info`

Get application information.

**Examples:**
```bash
insights apps info
insights apps info --json
```

### `insights apps risk`

Get applications grouped by risk score.

**Examples:**
```bash
insights apps risk
insights apps risk --hours 168
```

### `insights apps tags`

Get applications grouped by tag.

**Examples:**
```bash
insights apps tags
```

### `insights apps transfer`

Get data transfer by application.

**Options:**
- `--by-destination`: Group by destination instead of application

**Examples:**
```bash
insights apps transfer
insights apps transfer --by-destination
```

### `insights apps bandwidth`

Get application bandwidth info histogram.

**Examples:**
```bash
insights apps bandwidth
```

---

## Accelerated Commands

Query accelerated application metrics.

### `insights accelerated list`

List accelerated applications.

**Examples:**
```bash
insights accelerated list
insights accelerated list --limit 20
```

### `insights accelerated count`

Get accelerated application or user count.

**Options:**
- `--users`: Count users instead of applications

**Examples:**
```bash
insights accelerated count             # App count
insights accelerated count --users     # User count
```

### `insights accelerated performance`

Get performance boost metrics.

**Examples:**
```bash
insights accelerated performance
```

### `insights accelerated transfer`

Get data transfer metrics.

**Options:**
- `--per-app`: Show throughput per app

**Examples:**
```bash
insights accelerated transfer
insights accelerated transfer --per-app
```

### `insights accelerated response-time`

Get response time improvement metrics.

**Options:**
- `--per-app`: Show per-app breakdown

**Examples:**
```bash
insights accelerated response-time
insights accelerated response-time --per-app
```

### `insights accelerated histogram [METRIC]`

Get histogram for accelerated app metrics.

**Arguments:**
- `METRIC`: Metric type - `throughput`, `packet-loss`, `rtt`, `boost` (default: `throughput`)

**Examples:**
```bash
insights accelerated histogram throughput
insights accelerated histogram packet-loss
insights accelerated histogram rtt
```

---

## Sites Commands

Query site data.

### `insights sites list`

Get site count by type.

**Examples:**
```bash
insights sites list
```

### `insights sites traffic`

Get site traffic information.

**Examples:**
```bash
insights sites traffic
insights sites traffic --hours 168
```

### `insights sites bandwidth`

Get site bandwidth consumption histogram.

**Examples:**
```bash
insights sites bandwidth
```

### `insights sites sessions`

Get site session count.

**Examples:**
```bash
insights sites sessions
```

### `insights sites search [TERM]`

Search sites by location.

**Arguments:**
- `TERM`: Search term for site location

**Examples:**
```bash
insights sites search "US West"
insights sites search "Europe"
```

---

## Security Commands

Query PAB (Private Access Browser) security events.

### `insights security access`

Get PAB access events.

**Options:**
- `--blocked`: Show blocked events only
- `--breakdown`: Show breakdown
- `--histogram`: Show histogram

Options can be combined:

**Examples:**
```bash
insights security access                           # All access events
insights security access --blocked                 # Blocked only
insights security access --histogram               # Access histogram
insights security access --blocked --histogram     # Blocked histogram
insights security access --blocked --breakdown --histogram
```

### `insights security data`

Get PAB data events.

**Options:**
- `--blocked`: Show blocked events only
- `--breakdown`: Show breakdown
- `--histogram`: Show histogram

**Examples:**
```bash
insights security data
insights security data --blocked
insights security data --breakdown --histogram
```

---

## Monitoring Commands

Query monitored user metrics.

### `insights monitoring users`

Get monitored user count.

**Options:**
- `--histogram`: Show count histogram

**Examples:**
```bash
insights monitoring users
insights monitoring users --histogram
```

### `insights monitoring devices`

Get monitored device count.

**Options:**
- `--histogram`: Show count histogram

**Examples:**
```bash
insights monitoring devices
insights monitoring devices --histogram
```

### `insights monitoring experience`

Get user experience scores.

**Examples:**
```bash
insights monitoring experience
insights monitoring experience --hours 168
```

---

## Utility Commands

### `insights query [ENDPOINT]`

Execute a raw query against any endpoint. This is an escape hatch for endpoints not covered by dedicated commands.

**Arguments:**
- `ENDPOINT`: API endpoint path (e.g., `query/users/agent/user_list`)

**Examples:**
```bash
insights query "query/users/agent/connected_user_count"
insights query "query/applications/internal/application_list" --hours 48
```

### `insights test`

Test API connection and authentication.

**Examples:**
```bash
insights test
insights test --region europe
```

---

## Output Formats

### Table Output (default)

Commands display formatted tables with key information:

```
           Agent Users (showing 10 of 142)
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Username      ┃ Device   ┃ Platform ┃ Location   ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━┩
│ john.doe      │ LAPTOP01 │ Windows  │ US, CA     │
│ jane.smith    │ LAPTOP02 │ macOS    │ US, NY     │
└───────────────┴──────────┴──────────┴────────────┘
```

### JSON Output (`--json`)

Use `--json` flag for raw API responses, useful for scripting:

```bash
insights users count agent --json | jq '.data[0].user_count'
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SCM_CLIENT_ID` | OAuth2 client ID |
| `SCM_CLIENT_SECRET` | OAuth2 client secret |
| `SCM_TSG_ID` | Tenant Service Group ID |
| `INSIGHTS_CLIENT_ID` | Alternative client ID |
| `INSIGHTS_CLIENT_SECRET` | Alternative client secret |
| `INSIGHTS_TSG_ID` | Alternative TSG ID |

The CLI also loads from `.env` files in:
1. Current directory
2. `~/.insights-sdk/.env`
