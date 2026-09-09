# Smart Lab Incident Monitor — Schema Contract

> **Contract version:** 1
> **Status:** Authoritative

## Purpose

This document is the single source of truth for cross-service JSON models, field names, types, identifiers, timestamps, validation, correlation, and idempotency. Implementations must provide equivalent Pydantic models under `common/models/`, and contract tests must instantiate those models from representative JSON fixtures.

## Global JSON rules

- Every named domain/event model is a UTF-8 JSON object with `schema_version` equal to integer `1`. Collection, error, and other explicitly documented REST wrapper objects do not add this field.
- Field names use lowercase snake case. Enum values are defined in [`STATES_AND_ACTIONS.md`](STATES_AND_ACTIONS.md).
- Required fields must be present. Optional fields may be omitted; JSON `null` is accepted only where the documented type includes `null`.
- Event, write, command, and state-mutation models reject unknown fields.
- Numbers must be finite JSON numbers. `NaN`, positive/negative infinity, and booleans masquerading as numbers are rejected.
- Strings are trimmed only for validation; producers must not rely on receivers rewriting values.
- A timestamp is a timezone-aware ISO 8601 UTC string ending in `Z`, with second or finer precision.
- No model may contain credentials, tokens, arbitrary executable source, raw SQL/Flux, or untrusted MQTT wildcards.

Read-response models may gain an optional field within version 1 only when existing consumers ignore it safely and contract tests prove compatibility. Removing a field, making an optional field required, changing a type/meaning, or changing an enum requires a new schema version and migration plan.

## Identifier rules

Generated identifiers are a readable prefix followed by the lowercase canonical text of a UUIDv4 without braces. Hyphens in the UUID portion are retained. The same identifier is reused across retries; a retry must never generate a replacement ID.

| Object | Field | Prefix |
| --- | --- | --- |
| Generic event, raw telemetry, normalized observation, heartbeat, or status event | `event_id`, `heartbeat_id`, `status_event_id` | `evt_` |
| Generated device | `device_id` | `dev_` |
| Service instance | `service_id` | `svc_` |
| Alert | `alert_id` | `alt_` |
| Incident | `incident_id` | `inc_` |
| Recommendation | `recommendation_id` | `rec_` |
| Response action | `action_id` | `act_` |
| Command | `command_id` | `cmd_` |
| Command acknowledgment | `command_ack_id` | `cack_` |
| Operator | `operator_id` | `op_` |
| Operator action | `operator_action_id` | `opa_` |
| Notification | `notification_id` | `not_` |
| REST request | `request_id` | `req_` |

Human-readable `device_id` values are also permitted. They must match `^[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]$` or be a single lowercase alphanumeric character, be unique within the site, and contain none of `/`, `+`, or `#`. Service names, instance IDs, profile IDs, detector IDs, metric names, zones, and reason codes follow the same topic-safe principle; service names use lowercase kebab case and metric/profile/reason names use lowercase snake case.

`dedupe_key` is a deterministic opaque string of 1–200 printable ASCII characters. `idempotency_key` is a caller-generated opaque string of 8–128 printable ASCII characters. Neither is a secret.

## Timestamp ownership

| Field | Clock owner |
| --- | --- |
| `observed_at` | Producer that observed the physical/logical event. |
| `ingested_at` | Ingestion after validation and normalization. |
| `created_at` | Service creating the domain record. |
| `updated_at` | Domain producer on initial creation; persistence-owning service on an accepted PATCH/state mutation. |
| `last_seen_at` | Catalog server at receipt time; never copied from sender time. |
| `issued_at` | Response Manager immediately before command publication. |
| `expires_at` | Response Manager; later than `issued_at` and no more than 300 seconds after it. |
| `processed_at` | Response Manager after validating an operator intent. |

Receivers reject timestamps without a timezone. They may reject an event whose clock skew exceeds the device profile's accepted bound, but they retain the sender's original `observed_at` in validation evidence and never rewrite it as `last_seen_at`.

## Supporting value objects

### MetricDefinition

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `metric` | string | Yes | Lowercase snake case, 1–64 characters. |
| `unit` | string | Yes | Lowercase unit name, 1–32 characters. |
| `value_type` | string | Yes | Exactly `number` in version 1. |
| `required` | boolean | Yes | Whether every RawTelemetry event for this device must contain the metric. |

### HeartbeatPolicy

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `expected_interval_s` | integer | Yes | 1–300. |
| `stale_after_s` | integer | Yes | At least twice `expected_interval_s`, maximum 3600. |

### DeviceTopics

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `telemetry` | string | Yes | Canonical raw telemetry topic for the device. |
| `heartbeat` | string | Yes | Canonical raw heartbeat topic for the device. |
| `status` | string | Yes | Canonical raw status topic for the device. |
| `cmd` | string | Yes | Canonical command topic for the device. |
| `ack` | string | Yes | Canonical command-acknowledgment topic for the device. |

Every value must exactly match [`TOPICS.md`](TOPICS.md) for the global site and the record's `device_id`.

### DeviceRequestedSettings

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `site_id` | string | Yes | Must equal the Service Catalog global site ID. |
| `zone` | string | Yes | Topic-safe lowercase identifier, 1–64 characters. |
| `telemetry_interval_s` | integer | Yes | 1–3600. |
| `heartbeat_policy` | HeartbeatPolicy | Yes | Valid heartbeat policy. |
| `metrics` | array of MetricDefinition | Yes | 1–32 unique metric names. |
| `requested_topics` | DeviceTopics or null | No | If supplied, Device Catalog validates exact canonical equality; otherwise it generates them. |

### EvidenceItem

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `evidence_ref` | string | Yes | Unique within the alert; 1–128 printable characters. |
| `kind` | string | Yes | `current_observation`, `historical_window`, `device_status`, `publication_rate`, or `broker_health`. |
| `summary` | string | Yes | 1–500 characters; factual, not executable. |
| `source_ref` | string | Yes | Stable event ID or REST resource reference. |
| `observed_at` | UTC timestamp | Yes | Time represented by the evidence. |
| `details` | object | Yes | Bounded JSON scalar/array values; no secrets, queries, code, or nested objects deeper than two levels. |

### ToolDescriptor

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `tool_name` | string | Yes | One approved name from [`CONFIGURATION.md`](CONFIGURATION.md). |
| `service_name` | string | Yes | Logical owning provider. |
| `method` | string | Yes | Exactly `GET` in version 1. |
| `path_template` | string | Yes | Relative `/api/v1/...` path; no scheme/host. |
| `description` | string | Yes | 1–300 characters. |
| `allowed_query_parameters` | array of strings | Yes | Explicit allowlist; no duplicates. |

## Telemetry and device-event models

### RawTelemetry

One RawTelemetry object contains one device observation with one or more readings.

RawTelemetry is validated and transformed but is not archived as a separate version 1 series. NormalizedTelemetry is the authoritative persisted telemetry model.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `event_id` | string | Yes | `evt_` UUIDv4; MQTT idempotency key for this raw event. |
| `device_id` | string | Yes | Must equal the device ID in the topic. |
| `observed_at` | UTC timestamp | Yes | Set by Device Connector. |
| `readings` | object of metric → finite number | Yes | 1–32 entries; metrics/units must exist in Device Catalog. |
| `sequence` | integer or null | No | Non-negative and monotonically increasing per logical device while its simulator process runs. |

```json
{
  "schema_version": 1,
  "event_id": "evt_4cba1e0c-61e9-4aeb-8368-e5691779f534",
  "device_id": "temp-lab-a-01",
  "observed_at": "2026-09-08T12:00:00Z",
  "readings": {"temperature_c": 22.4},
  "sequence": 1042
}
```

### NormalizedTelemetry

One NormalizedTelemetry object contains exactly one canonical metric observation. A RawTelemetry event with multiple readings therefore produces multiple objects with distinct `event_id` values and the same `source_event_id`.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `event_id` | string | Yes | New `evt_` UUIDv4 for this normalized observation. |
| `source_event_id` | string | Yes | RawTelemetry `event_id`. |
| `device_id` | string | Yes | Registered, topic-safe device ID. |
| `metric` | string | Yes | Canonical metric in Device Catalog. |
| `value` | finite number | Yes | Boolean is invalid; anomaly thresholds are evaluated by Detection, not Ingestion. |
| `unit` | string | Yes | Must equal the catalog unit for `metric`. |
| `observed_at` | UTC timestamp | Yes | Copied unchanged from accepted RawTelemetry. |
| `ingested_at` | UTC timestamp | Yes | Set by Ingestion. |
| `quality` | string | Yes | `ok` or `suspect`. |
| `source_topic` | string | Yes | Exact validated raw topic from which the event arrived. |

```json
{
  "schema_version": 1,
  "event_id": "evt_598b734c-c983-42da-aaf9-8d33df50cf21",
  "source_event_id": "evt_4cba1e0c-61e9-4aeb-8368-e5691779f534",
  "device_id": "temp-lab-a-01",
  "metric": "temperature_c",
  "value": 22.4,
  "unit": "celsius",
  "observed_at": "2026-09-08T12:00:00Z",
  "ingested_at": "2026-09-08T12:00:00.120Z",
  "quality": "ok",
  "source_topic": "smartlab/polito-smartlab/devices/temp-lab-a-01/telemetry"
}
```

### Heartbeat

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `heartbeat_id` | string | Yes | `evt_` UUIDv4. |
| `device_id` | string | Yes | Must equal the topic device ID. |
| `observed_at` | UTC timestamp | Yes | Set by Device Connector. |
| `sequence` | integer or null | No | Non-negative; monotonic for the current connector process. |
| `connector_instance_id` | string or null | No | Must equal Device Connector's bootstrap `INSTANCE_ID` when supplied. |

### DeviceStatusUpdate

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `status_event_id` | string | Yes | `evt_` UUIDv4. |
| `device_id` | string | Yes | Must equal the topic/path device ID. |
| `status` | string | Yes | Device status enum. |
| `reason` | string | Yes | Lowercase snake-case reason code, 1–64 characters. |
| `observed_at` | UTC timestamp | Yes | Set by Device Connector. |

## Registration and catalog record models

### DeviceRegistration

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `device_id` | string | Yes | Unique topic-safe human ID or `dev_` UUIDv4. |
| `display_name` | string | Yes | 1–100 characters. |
| `device_type` | string | Yes | Lowercase snake case, 1–64 characters; never named `type`. |
| `managed_by_service_id` | string | Yes | Registered Device Connector `svc_` ID. |
| `capabilities` | array of strings | Yes | Unique lowercase snake-case capability names. |
| `command_capable` | boolean | Yes | Must agree with `allowed_actions`. |
| `allowed_actions` | array of strings | Yes | Unique executable actions only: `increase_monitoring`, `set_safe_mode`, `logical_isolation`. |
| `detector_profile_id` | string | Yes | Lowercase snake-case reference. Device Catalog treats it as opaque; Detection must resolve it to a configured profile. |
| `requested_settings` | DeviceRequestedSettings | Yes | Proposed configuration; Device Catalog validates/resolves it. |

If `command_capable` is false, `allowed_actions` must be empty. If true, it must contain at least one action implemented by the managing Device Connector.

### DeviceRecord

DeviceRecord contains all DeviceRegistration fields except `requested_settings`, plus these authoritative fields:

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `settings` | DeviceRequestedSettings without `requested_topics` | Yes | Resolved catalog settings. |
| `topics` | DeviceTopics | Yes | Canonical generated/validated topics. |
| `status` | string | Yes | Device status enum; initially `offline`. |
| `last_seen_at` | UTC timestamp or null | Yes | Set by Device Catalog receipt time. |
| `registered_at` | UTC timestamp | Yes | Set on first registration. |
| `updated_at` | UTC timestamp | Yes | Set on accepted record/config change. |
| `config_version` | integer | Yes | Starts at 1; increases after a configuration change. |

### DeviceConfig

DeviceConfig is the configuration-only projection returned by Device Catalog. It contains exactly `schema_version`, `device_id`, `display_name`, `device_type`, `managed_by_service_id`, `capabilities`, `command_capable`, `allowed_actions`, `detector_profile_id`, `settings`, `topics`, and `config_version` from DeviceRecord. It excludes `status`, `last_seen_at`, `registered_at`, and `updated_at`.

### ServiceRegistration

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `service_id` | string | Yes | `svc_` UUIDv4 reused for the process lifetime. |
| `service_name` | string | Yes | Lowercase kebab case, 1–63 characters. |
| `instance_id` | string | Yes | Topic-safe lowercase identifier, 1–63 characters. |
| `base_url` | string | Yes | Absolute HTTP URL without trailing slash. |
| `health_url` | string | Yes | Exactly `base_url + "/health"`. |
| `version` | string | Yes | Semantic version string. |
| `capabilities` | array of strings | Yes | Unique lowercase snake-case capability names. |

### ServiceRecord

ServiceRecord contains all ServiceRegistration fields plus:

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `status` | string | Yes | Service status enum; initially `starting`. |
| `registered_at` | UTC timestamp | Yes | Service Catalog server time on first registration. |
| `last_seen_at` | UTC timestamp | Yes | Service Catalog server receipt time. |
| `status_reason` | string or null | Yes | Short non-secret explanation, maximum 300 characters. |

## Detection and incident models

### Alert

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `alert_id` | string | Yes | `alt_` UUIDv4. |
| `incident_id` | string | Yes | `inc_` UUIDv4 allocated by Detection. |
| `device_id` | string | Yes | Registered device ID. |
| `detector_id` | string | Yes | Lowercase snake-case detector/rule ID. |
| `severity` | string | Yes | Severity enum. |
| `title` | string | Yes | 1–160 characters. |
| `description` | string | Yes | 1–1000 characters. |
| `observed_at` | UTC timestamp | Yes | Time of the triggering observation/window end. |
| `created_at` | UTC timestamp | Yes | Set by Detection. |
| `evidence` | array of EvidenceItem | Yes | 1–20 items; references must be unique. |
| `dedupe_key` | string | Yes | Stable for the same detector/device/condition during its cooldown. |

### Incident

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `incident_id` | string | Yes | `inc_` UUIDv4; matches the originating Alert. |
| `primary_alert_id` | string | Yes | Originating `alt_` ID. |
| `device_id` | string | Yes | Registered device ID. |
| `severity` | string | Yes | Severity enum. |
| `status` | string | Yes | Incident status enum; initially `new`. |
| `summary` | string | Yes | 1–500 characters. |
| `current_recommendation_id` | string or null | Yes | Current `rec_` ID after accepted recommendation. |
| `last_action_id` | string or null | Yes | Most recent `act_` ID. |
| `created_at` | UTC timestamp | Yes | Set by Detection. |
| `updated_at` | UTC timestamp | Yes | Initially set by Detection; subsequently set by Operations Store on an accepted transition. |
| `version` | integer | Yes | Starts at 1; increments for every accepted mutation. |

### Recommendation

Version 1 has no separate Investigation model. The validated `explanation` and `evidence_refs` in Recommendation are the persisted bounded investigation result.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `recommendation_id` | string | Yes | `rec_` UUIDv4. |
| `incident_id` | string | Yes | Existing incident ID. |
| `action` | string | Yes | Recommendation/action enum. |
| `parameters` | object | Yes | Exact action-specific object from [`STATES_AND_ACTIONS.md`](STATES_AND_ACTIONS.md). |
| `confidence` | number | Yes | Finite value from 0.0 through 1.0. |
| `explanation` | string | Yes | 1–1500 characters. |
| `evidence_refs` | array of strings | Yes | 1–20 references present in the alert/approved retrieved context. |
| `requires_confirmation` | boolean | Yes | Advisory hint; Response Manager recomputes from policy. |
| `created_at` | UTC timestamp | Yes | Set by Agentic AI Investigation. |

```json
{
  "schema_version": 1,
  "recommendation_id": "rec_51ff9361-26f7-4c2c-bbcc-bf3902ef6981",
  "incident_id": "inc_e93f91fc-c768-4e8f-a275-f29787619e90",
  "action": "set_safe_mode",
  "parameters": {},
  "confidence": 0.86,
  "explanation": "The observation violates the device range and recent history supports a sensor fault.",
  "evidence_refs": ["temperature-range-event"],
  "requires_confirmation": true,
  "created_at": "2026-09-08T12:00:05Z"
}
```

## Response and command models

### Command

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `command_id` | string | Yes | `cmd_` UUIDv4. |
| `action_id` | string | Yes | Existing `act_` ID. |
| `incident_id` | string | Yes | Existing incident ID. |
| `device_id` | string | Yes | Must equal target topic device ID. |
| `action` | string | Yes | `increase_monitoring`, `set_safe_mode`, or `logical_isolation`. |
| `parameters` | object | Yes | Exact action-specific object; unknown fields rejected. |
| `issued_at` | UTC timestamp | Yes | Set by Response Manager. |
| `expires_at` | UTC timestamp | Yes | Later than `issued_at`, maximum 300 seconds later. |

```json
{
  "schema_version": 1,
  "command_id": "cmd_b436baf0-6d87-49f1-977e-aebe421ff6c3",
  "action_id": "act_f425c668-c452-48cc-a1f7-cec5038b42ce",
  "incident_id": "inc_e93f91fc-c768-4e8f-a275-f29787619e90",
  "device_id": "temp-lab-a-01",
  "action": "set_safe_mode",
  "parameters": {},
  "issued_at": "2026-09-08T12:00:15Z",
  "expires_at": "2026-09-08T12:01:15Z"
}
```

### CommandAck

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `command_ack_id` | string | Yes | `cack_` UUIDv4; MQTT idempotency key for this acknowledgment event. |
| `command_id` | string | Yes | Corresponding `cmd_` ID. |
| `action_id` | string | Yes | Corresponding `act_` ID. |
| `incident_id` | string | Yes | Corresponding `inc_` ID. |
| `device_id` | string | Yes | Must equal topic/Command device ID. |
| `status` | string | Yes | Command acknowledgment status enum. |
| `reason` | string | Yes | Non-empty lowercase reason code or concise human-readable reason, maximum 300 characters. |
| `observed_at` | UTC timestamp | Yes | Set by Device Connector. |

### ActionRecord

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `action_id` | string | Yes | `act_` UUIDv4. |
| `incident_id` | string | Yes | Existing incident ID. |
| `recommendation_id` | string | Yes | Recommendation that led to this policy decision. |
| `device_id` | string | Yes | Target device ID. |
| `command_id` | string or null | Yes | `cmd_` ID after command creation; null for non-command outcomes. |
| `action` | string | Yes | Recommendation/action enum. |
| `parameters` | object | Yes | Exact action-specific object. |
| `risk` | string | Yes | Action risk enum. |
| `status` | string | Yes | Action status enum. |
| `requested_by` | string | Yes | Literal `automatic` or an `op_` operator ID. |
| `reason` | string | Yes | 1–500 characters explaining policy/result. |
| `confirmation_expires_at` | UTC timestamp or null | Yes | Set when confirmation is required and retained thereafter; null for actions that never require confirmation. |
| `created_at` | UTC timestamp | Yes | Set by Response Manager. |
| `updated_at` | UTC timestamp | Yes | Initially set by Response Manager; subsequently set by Operations Store on an accepted action transition. |

### OperatorRecord

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `operator_id` | string | Yes | `op_` UUIDv4. |
| `telegram_user_id` | integer | Yes | Positive 64-bit Telegram user identifier; not a bot token. |
| `display_name` | string | Yes | 1–100 characters. |
| `role` | string | Yes | `viewer` or `operator`. |
| `enabled` | boolean | Yes | Disabled operators receive no notification and cannot act. |
| `minimum_severity` | string | Yes | Severity routing threshold. |

### OperatorActionIntent

This is the body accepted by Response Manager from Dashboard or Telegram Bot.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `operator_action_id` | string | Yes | Caller-generated `opa_` UUIDv4. |
| `incident_id` | string | Yes | Existing incident ID. |
| `operator_id` | string | Yes | Existing enabled operator ID. |
| `action` | string | Yes | Operator-action enum. |
| `recommendation_id` | string or null | Yes | Required for `approve`/`reject`; null for `acknowledge`. |
| `incident_version` | integer | Yes | Version observed by the user interface; positive. |
| `observed_at` | UTC timestamp | Yes | Time the operator submitted the intent. |
| `idempotency_key` | string | Yes | 8–128 printable characters; must match the HTTP header. |
| `note` | string or null | Yes | Maximum 500 characters. |

### OperatorAction

OperatorAction contains every OperatorActionIntent field plus:

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `accepted` | boolean | Yes | Whether the intent won validation/concurrency checks. |
| `result_code` | string | Yes | `accepted`, `duplicate`, `conflict`, `forbidden`, or `invalid_state`. |
| `processed_at` | UTC timestamp | Yes | Set by Response Manager. |

### Notification

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `notification_id` | string | Yes | `not_` UUIDv4. |
| `incident_id` | string | Yes | Existing incident ID. |
| `severity` | string | Yes | Severity enum. |
| `kind` | string | Yes | Notification-kind enum. |
| `title` | string | Yes | 1–160 characters. |
| `message` | string | Yes | 1–1000 characters; no secrets. |
| `requires_response` | boolean | Yes | True only when controlled operator input is expected. |
| `created_at` | UTC timestamp | Yes | Set by Response Manager. |

## REST support models

### GlobalPlatformConfig

The exact object and constraints are defined in [`CONFIGURATION.md`](CONFIGURATION.md). It contains `schema_version`, `config_version`, `site_id`, `mqtt`, `service_heartbeat`, and `discovery_cache`; it never contains a secret.

### TelemetrySummary

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `device_id` | string | Yes | Queried device. |
| `metric` | string | Yes | Canonical metric. |
| `unit` | string | Yes | Canonical unit. |
| `count` | integer | Yes | Non-negative. |
| `minimum` | finite number or null | Yes | Null when count is zero. |
| `maximum` | finite number or null | Yes | Null when count is zero. |
| `mean` | finite number or null | Yes | Null when count is zero. |
| `latest_value` | finite number or null | Yes | Null when count is zero. |
| `latest_observed_at` | UTC timestamp or null | Yes | Null when count is zero. |

### IncidentTransitionRequest

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `expected_version` | integer | Yes | Must equal current Incident `version`. |
| `status` | string | Yes | Target incident status. |
| `reason` | string | Yes | 1–500 characters. |
| `recommendation_id` | string or null | Yes | Current recommendation when applicable. |
| `action_id` | string or null | Yes | Related action when applicable. |

### ActionTransitionRequest

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `expected_status` | string | Yes | Must equal the stored ActionRecord status. |
| `status` | string | Yes | Target ActionRecord status permitted by the action lifecycle. |
| `reason` | string | Yes | 1–500 characters. |
| `command_id` | string or null | Yes | Set to the generated `cmd_` ID when transitioning to `issued`; otherwise preserves/null as applicable. |

### OperatorActionResult

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `operator_action` | OperatorAction | Yes | Persisted result of the submitted intent. |
| `incident` | Incident | Yes | Current authoritative incident after processing. |
| `action_record` | ActionRecord or null | Yes | Related record for approve/reject when created; null for acknowledgment. |

### ServiceHeartbeatRequest

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `status` | string | Yes | `healthy` or `degraded`. |
| `observed_at` | UTC timestamp | Yes | Sender time; Service Catalog still sets `last_seen_at`. |

### ServiceStatusRequest

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `status` | string | Yes | Service status enum. |
| `reason` | string | Yes | 1–300 non-secret characters. |
| `observed_at` | UTC timestamp | Yes | Sender time. |

### HealthResponse

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | integer | Yes | Exactly `1`. |
| `service_name` | string | Yes | Logical service name. |
| `service_id` | string | Yes | Current process service ID. |
| `status` | string | Yes | Service status enum. |
| `version` | string | Yes | Service semantic version. |
| `checked_at` | UTC timestamp | Yes | Server time. |
| `dependencies` | object | Yes | Dependency name → `healthy`, `degraded`, or `unavailable`; no URLs or secrets. |

### ErrorResponse

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": {"field": "device_id", "reason": "topic and payload IDs differ"},
    "request_id": "req_234f720b-3df0-42d0-92a9-acfb4bd3f82e"
  }
}
```

`code`, `message`, `details`, and `request_id` are required. Details contain bounded non-secret JSON and must not expose stack traces, credentials, SQL/Flux, or raw rejected payloads.

### CollectionResponse

Every collection response is an object containing:

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `items` | array | Yes | Homogeneous resource models. |
| `count` | integer | Yes | Number of items in this response. |
| `limit` | integer | No | Echoed when pagination applies. |
| `offset` | integer | No | Echoed when pagination applies. |
| `window` | object | No | Included for time-window queries; contains `start` and end-exclusive `end`. |

## Idempotency and correlation

- MQTT uses the payload's stable object/event ID. A QoS 1 redelivery with the same ID and identical content returns or reuses the original processing result; the same ID with different content is rejected and logged as a conflict.
- Retryable POST requests require `Idempotency-Key`. The key is scoped to provider, endpoint, and caller service ID.
- Replaying the same key with the same validated body returns the stored response without repeating side effects. Reusing it with a different body returns HTTP 409.
- `alert_id`, `incident_id`, `recommendation_id`, `action_id`, `command_id`, `command_ack_id`, `operator_action_id`, and `notification_id` remain unchanged throughout one correlated response flow.
- A normalized observation preserves `source_event_id`; evidence references stable observations/resources rather than embedding unbounded histories.

## Telemetry rejection rules

Ingestion rejects an event before any InfluxDB write or normalized publication when:

- JSON/schema validation fails;
- the topic site/device does not match the configured site and payload;
- the device is unknown;
- a required metric is missing or an unknown metric is present;
- a value is non-finite, boolean, or paired with an invalid type/unit definition;
- an ID is malformed; or
- a timestamp is invalid under the device profile's accepted clock policy.

Rejected events are counted and logged with topic, stable event ID when safely available, and reason. Logs do not include secrets or an unbounded raw payload.

A finite value outside a detector's expected range is not rejected by Ingestion. It is persisted/published as normalized telemetry so Detection can create evidence and an alert. Detection thresholds belong only to Detection configuration.
