# Smart Lab Incident Monitor — Configuration Contract

> **Contract version:** 1
> **Status:** Authoritative

## Purpose

This document defines where configuration originates, which component owns it, how services bootstrap and discover dependencies, how secrets are isolated, and how temporary catalog failures are handled. It prevents peer URLs, credentials, device policy, and response policy from being duplicated across services.

## Configuration principles

1. A service starts with only its own identity/address, the Service Catalog URL, and secrets that it alone requires.
2. Peer endpoints and non-secret platform configuration are discovered through Service Catalog.
3. Device-specific configuration is obtained through Device Catalog.
4. Secrets never enter Git, catalog records, MQTT payloads, REST bodies, snapshots, logs, or error details.
5. A service may use a bounded last-known-good cache during a temporary catalog outage but must never silently substitute a hard-coded peer URL.
6. Configuration is validated before network clients or background workers start.
7. Conflicting values from two authoritative owners are an error; services must not merge competing sources silently.

## Authoritative ownership

| Configuration category | Authoritative location | Examples | Consumers |
| --- | --- | --- | --- |
| Local service bootstrap | Environment or one optional per-service bootstrap JSON file | `SERVICE_CATALOG_URL`, `SERVICE_NAME`, `INSTANCE_ID`, `BASE_URL` | The service being started. |
| Secrets | Environment variables or Docker secrets | InfluxDB token/password, Telegram bot token, LLM API key | Only the service that needs each secret. |
| Non-secret platform configuration | Service Catalog bootstrap JSON and REST | Site ID, broker endpoint, topic root, MQTT session settings, heartbeat and cache defaults | All application services. |
| Logical device configuration | Device Catalog JSON snapshot and REST | Metrics, units, intervals, topics, capabilities, allowed actions, detector profile ID | Device Connector, Ingestion, Detection, Response Manager. |
| Detector definitions | Detection-owned tracked configuration | Rule types, thresholds, historical-window parameters, cooldown/deduplication policy | Detection only. |
| Response policy | Response Manager-owned tracked configuration | Action risk, confirmation requirement, confirmation timeout, command timeout | Response Manager only. |
| Operator records and preferences | Operations Store | Role, Telegram user ID, enabled state, minimum severity | Response Manager and Telegram Bot through REST. |
| Infrastructure initialization | Tracked `.env.example`, Compose configuration, and local untracked `.env` | InfluxDB organization, bucket, initial username, and local container settings | Compose and Ingestion as applicable. |

## Minimal service bootstrap

Every application service receives these values before contacting another application service:

| Name | Type and constraint | Required | Meaning |
| --- | --- | --- | --- |
| `SERVICE_NAME` | Lowercase kebab-case string, 1–63 characters | Yes | Logical service name, such as `ingestion` or `response-manager`. |
| `INSTANCE_ID` | Topic-safe lowercase identifier, 1–63 characters | Yes | Distinguishes simultaneously running instances of the same service. |
| `BASE_URL` | Absolute HTTP URL without a trailing slash | Yes | Address advertised to Service Catalog; `/health` is appended for the health URL. |
| `SERVICE_CATALOG_URL` | Absolute HTTP URL without a trailing slash | Yes | The only peer URL supplied directly at bootstrap. For Service Catalog itself, this equals `BASE_URL`. |
| `SERVICE_BOOTSTRAP_PATH` | Local filesystem path | No | Optional JSON source for the four values above. It contains no secrets. |

If `SERVICE_BOOTSTRAP_PATH` is supplied, the loader reads that file first and then applies non-empty environment values for the four named fields as explicit overrides. Unknown JSON keys, missing required values, malformed URLs, and invalid identifiers cause startup failure. Environment variables not named in this contract are not treated as bootstrap configuration.

At process start, each service generates one UUIDv4 `service_id` with the `svc_` prefix and reuses it for all registration retries and heartbeats during that process lifetime. `INSTANCE_ID` is deployment identity; `service_id` identifies the current running instance record. A restarted process may receive a new `service_id`, while the previous record becomes stale through the catalog heartbeat policy.

The canonical application `SERVICE_NAME` values are `service-catalog`, `device-catalog`, `device-connector`, `ingestion`, `operations-store`, `detection`, `agentic-ai`, `response-manager`, `dashboard`, and `telegram-bot`. Mosquitto and InfluxDB are infrastructure dependencies rather than application service registrations.

## Global platform configuration

Service Catalog owns and returns the following non-secret object from `GET /api/v1/config/global`:

```json
{
  "schema_version": 1,
  "config_version": 1,
  "site_id": "polito-smartlab",
  "mqtt": {
    "host": "mosquitto",
    "port": 1883,
    "topic_root": "smartlab",
    "keepalive_s": 60,
    "clean_session": true,
    "tls_enabled": false
  },
  "service_heartbeat": {
    "interval_s": 30,
    "stale_after_s": 90
  },
  "discovery_cache": {
    "ttl_s": 30,
    "max_stale_s": 300
  }
}
```

The version 1 demo uses the lowercase topic root `smartlab`, site ID `polito-smartlab`, clean sessions, and an unencrypted broker on the trusted local Compose network. Topic-specific QoS and retain values come only from [`TOPICS.md`](TOPICS.md); a global default must not override them.

`config_version` increases whenever the Service Catalog bootstrap object changes. Consumers replace their cached object atomically after validating the complete new version.

## Device configuration

Device Catalog owns the resolved configuration for each logical device. The registration request may propose settings, but the returned catalog record is authoritative. It contains:

- identity: `device_id`, `display_name`, `device_type`, `site_id`, `zone`, and `managed_by_service_id`;
- metric definitions: canonical metric name, numeric value type, unit, and whether the metric is required;
- publication settings: telemetry interval and heartbeat policy;
- the five device topic paths generated or validated against [`TOPICS.md`](TOPICS.md);
- `command_capable`, declared capabilities, and the allowed-action whitelist;
- `detector_profile_id`; and
- an integer `config_version` that increases after a configuration change.

Dynamic topic fragments must be lowercase and must not contain `/`, `+`, or `#`. Device Catalog rejects a registration whose proposed topics do not exactly match the canonical topic helper. A non-command-capable device has no executable actions in its whitelist; `notify_operator_only` and `no_immediate_action` are response outcomes rather than device commands.

Device Connector refreshes its device configuration after `config_version` changes or after the cache TTL. Detection uses `detector_profile_id` to select a locally tracked profile. Response Manager always refreshes an expired whitelist before authorizing a command.

Device Catalog owns the device-to-profile assignment but treats `detector_profile_id` as an opaque, syntactically validated reference. Detection owns the referenced definitions and reports a configuration error rather than inventing a fallback when an assigned profile does not exist.

## Detection configuration

Detection owns a tracked, non-secret configuration file containing versioned detector profiles. Each profile contains:

| Field | Constraint |
| --- | --- |
| `schema_version` | Integer `1`. |
| `profile_id` | Lowercase snake-case identifier. |
| `rules` | Non-empty list of supported rule objects. |
| `rule_id` | Unique within the profile. |
| `rule_type` | One of `range`, `stuck_window`, `rate_window`, `heartbeat_timeout`, or `broker_health`. |
| `metric` | Required for metric-based rules and absent for service/broker rules. |
| `parameters` | Strict object appropriate to the selected rule type. |
| `severity` | A value defined in [`STATES_AND_ACTIONS.md`](STATES_AND_ACTIONS.md). |
| `cooldown_s` | Non-negative integer used by the alert deduplication policy. |

Threshold values and window sizes are demo data, not catalog-owned platform settings. Changing a value without changing this configuration shape is a non-breaking configuration change. Detection validates the entire file at startup and refuses a profile containing an unknown rule type, field, metric, or unit.

## Response policy configuration

Response Manager owns one tracked, non-secret policy file. It maps every recommendation/action value to its risk, whether it is executable, whether human confirmation is required, `confirmation_timeout_s`, and `command_timeout_s`. The version 1 risk/authorization mappings are fixed by [`STATES_AND_ACTIONS.md`](STATES_AND_ACTIONS.md).

The file must contain exactly one entry for every action value. Unknown actions and duplicate entries fail startup. Device Catalog's whitelist can narrow what Response Manager authorizes but cannot reduce the risk or confirmation requirement defined by Response Manager. Recommendation fields supplied by Agentic AI Investigation are advisory and cannot override this policy.

For executable actions, `command_timeout_s` is greater than zero and no more than 300 seconds. For confirmation-required actions, `confirmation_timeout_s` is 60–86400 seconds; it is null for other actions. The resulting confirmation deadline is recorded in ActionRecord, and command expiry is recorded in Command rather than inferred by Device Connector.

## Approved AI tool configuration

Service Catalog returns only approved, read-only tool descriptors. Version 1 permits these logical tools:

| Tool name | Owning provider | Relative path | Allowed inputs |
| --- | --- | --- | --- |
| `get_device` | Device Catalog | `/api/v1/devices/{device_id}` | Path `device_id`. |
| `get_device_config` | Device Catalog | `/api/v1/devices/{device_id}/config` | Path `device_id`. |
| `get_recent_telemetry` | Ingestion | `/api/v1/telemetry/recent` | `device_id`, optional `metric` and `limit`. |
| `get_telemetry_window` | Ingestion | `/api/v1/telemetry/window` | Required `device_id`, `start`, `end`; optional `metric`, `limit`. |
| `get_telemetry_summary` | Ingestion | `/api/v1/telemetry/summary` | Required `device_id`, `start`, `end`; optional `metric`. |
| `get_incident` | Operations Store | `/api/v1/incidents/{incident_id}` | Path `incident_id`. |
| `list_alerts` | Operations Store | `/api/v1/alerts` | Optional `incident_id`, `device_id`, `severity`, `detector_id`, `start`, `end`, `limit`, and `offset`. |
| `list_recommendations` | Operations Store | `/api/v1/recommendations` | Optional `incident_id`, `action`, `start`, `end`, `limit`, and `offset`. |

Tool descriptors contain a logical name, owning `service_name`, HTTP method, relative path template, description, and allowed query parameters. Every version 1 AI tool uses `GET`. Descriptors never contain credentials, arbitrary hostnames, raw SQL/Flux, mutation methods, or caller-supplied broker topics. Agentic AI Investigation resolves the provider's current base URL through Service Catalog.

## Secrets and service scoping

| Secret | Allowed recipient | Forbidden locations |
| --- | --- | --- |
| `INFLUXDB_TOKEN` | Ingestion only | Other services, catalogs, APIs, MQTT, logs, snapshots, Git. |
| `DOCKER_INFLUXDB_INIT_PASSWORD` | InfluxDB container initialization only | Application services, catalogs, APIs, logs, Git values. |
| `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN` | InfluxDB initialization and Ingestion local environment only | Other services, catalogs, APIs, logs, Git values. |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot only | Operator records, catalogs, notifications, logs, Git. |
| `LLM_API_KEY` | Agentic AI Investigation only | Tool descriptors, prompts persisted as records, catalogs, logs, Git. |

`.env.example` contains variable names and safe placeholders only. The real `.env` remains ignored and local. Secrets are redacted as `[REDACTED]` if a diagnostic must mention that a value exists. A service reports only `configured: true|false` in health metadata and never returns a secret value or a reversible derivative.

Non-secret InfluxDB settings—`INFLUXDB_URL`, `INFLUXDB_ORG`, and `INFLUXDB_BUCKET`—are supplied only to Ingestion and infrastructure initialization. Their non-secret status does not permit another service to receive or use them.

Operations Store may receive `OPERATORS_BOOTSTRAP_PATH`, pointing to a local untracked JSON file of OperatorRecord values. It validates and idempotently seeds those records on startup; the file never contains `TELEGRAM_BOT_TOKEN`. `.env.example` may show a safe example path but must not contain real Telegram user IDs.

## Startup and discovery sequence

Except for Service Catalog's self-bootstrap, every service starts in this order:

1. Load and validate local bootstrap values and service-scoped secrets.
2. Generate the process-lifetime `service_id`.
3. Register with Service Catalog.
4. Fetch and validate global platform configuration.
5. Discover required peer instances by logical service name.
6. Fetch service-specific catalog configuration, such as device records or approved tools.
7. Construct network clients and subscribe to the exact MQTT topics owned by the service.
8. Begin service heartbeats and report readiness.

Service Catalog loads its tracked bootstrap JSON and last valid atomic snapshot, exposes `/health`, and then accepts registrations. Device Catalog loads its tracked initial device JSON and last valid atomic snapshot before accepting registrations. Snapshot files are implementation persistence owned by their respective catalog and are never shared as files with callers.

## Cache and outage behavior

- A discovery or configuration response is fresh for `ttl_s`, which is 30 seconds in version 1.
- On refresh failure, a service may use its last validated object until its age reaches `max_stale_s`, which is 300 seconds.
- While using stale data, `/health` reports `degraded` and names the unavailable dependency without exposing URLs containing credentials.
- After `max_stale_s`, the service reports dependency unavailability and rejects operations requiring that dependency with HTTP 503.
- Safety-sensitive authorization never proceeds with an expired device whitelist or expired response policy.
- A successful refresh validates the full object and replaces the cache atomically; partial objects are never merged into a valid cache entry.
- A process with no previously validated value cannot invent a fallback and remains unready until discovery succeeds.

## Configuration change rules

- A change to a cross-service field name, type, meaning, owner, or required/optional status is a contract change.
- A new detector threshold value, device instance, operator record, or peer instance is a data/configuration change when it conforms to version 1 schemas.
- A service ignores no unknown configuration fields silently; strict configuration objects reject them.
- Runtime configuration changes are observed no later than the configured cache TTL unless a service is unavailable.
- A catalog snapshot is written through atomic replacement under a process lock so readers never observe a partially written file.

## Version 1 implementation defaults behind stable interfaces

| Choice | Version 1 default | Stable boundary |
| --- | --- | --- |
| Catalog persistence | Locked in-memory dictionaries with atomic JSON snapshots | Catalog REST models and endpoints. |
| Operations persistence | SQLite | Operations Store REST models and endpoints. |
| Telegram delivery | Long polling | Notification MQTT and OperatorActionIntent REST. |
| Dashboard updates | REST polling | Catalog, Ingestion, Operations Store, and Response Manager APIs. |
| AI provider | Provider adapter plus deterministic fake for automated tests | Validated Recommendation and approved read-only tools. |
| Telemetry archive | Persist normalized observations only | Ingestion history APIs. |
| MQTT security | Anonymous broker on the trusted local Compose network | Topic, payload, and QoS contracts. |
| Advanced reliability | Bounded retries, metrics/logging, and idempotency without a DLQ/outbox | Stable IDs and persistence-before-publication ordering. |

Changing one of these internal implementations without changing its stable boundary is not a version 1 contract break. Introducing a new externally visible field, state, topic, endpoint, or ownership rule follows [`README.md`](README.md) change control.
