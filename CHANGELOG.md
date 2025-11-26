# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-26

### Added

- Initial release of the Prisma Access Insights SDK
- **SDK Client** (`InsightsClient` and `AsyncInsightsClient`)
  - OAuth2 authentication with automatic token refresh
  - Retry logic with exponential backoff for transient failures
  - Support for all four regions (americas, europe, asia, apac)
  - Context manager support for proper resource cleanup

- **CLI Tool** (`insights`)
  - Organized command groups: users, apps, accelerated, sites, security, monitoring
  - Common options: `--hours`, `--json`, `--limit`, `--region`, `--verbose`
  - Rich console output with formatted tables

- **User Commands**
  - `insights users list [agent|branch|agentless|all]` - List users by type
  - `insights users count [agent|branch|agentless]` - Get connected user counts
  - `insights users sessions` - List user sessions
  - `insights users devices` - List agent devices
  - `insights users risky` - Get risky user counts
  - `insights users active` - Get active user counts
  - `insights users histogram` - User count over time
  - `insights users entities` - Connected entity counts
  - `insights users versions` - Agent version distribution

- **Application Commands**
  - `insights apps list` - List applications
  - `insights apps info` - Application details
  - `insights apps risk` - Apps by risk score
  - `insights apps tags` - Apps by tag
  - `insights apps transfer` - Data transfer metrics
  - `insights apps bandwidth <app>` - Bandwidth histogram for specific app

- **Site Commands**
  - `insights sites list` - Site count by type
  - `insights sites traffic` - Site traffic information
  - `insights sites bandwidth` - Bandwidth consumption histogram
  - `insights sites sessions` - Site session counts
  - `insights sites search <term>` - Search sites by location

- **Security Commands** (PAB - requires additional permissions)
  - `insights security access` - Access events with `--blocked`, `--breakdown`, `--histogram` flags
  - `insights security data` - Data events with `--blocked` flag

- **Monitoring Commands**
  - `insights monitoring users` - Monitored user counts
  - `insights monitoring devices` - Monitored device counts
  - `insights monitoring experience` - User experience scores

- **Accelerated Application Commands**
  - `insights accelerated list` - List accelerated applications
  - `insights accelerated count` - Application/user counts
  - `insights accelerated performance` - Performance boost metrics
  - `insights accelerated transfer` - Data transfer metrics
  - `insights accelerated response-time` - Response time improvements
  - `insights accelerated histogram` - Various histogram metrics

- **Utility Commands**
  - `insights test` - Test API connection
  - `insights query <endpoint>` - Raw query any endpoint

- **Pydantic Models**
  - `FilterRule` - Query filter construction
  - `QueryRequest` - Request body builder
  - `Region` - API region enumeration
  - `Operator` - Filter operators

- **Test Suite**
  - 260 unit tests with mocked HTTP responses
  - Integration test suite for real API validation
  - pytest fixtures for common test scenarios

### Notes

- Some endpoints (accelerated, monitoring, security) may require additional tenant permissions
- Agent-type endpoints require `platform_type` filter (added automatically by CLI)
- Histogram endpoints require histogram configuration (added automatically by CLI)

[0.1.0]: https://github.com/antoncoleman/insights-sdk/releases/tag/v0.1.0
