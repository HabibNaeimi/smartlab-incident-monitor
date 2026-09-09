# Smart Lab Incident Monitor — REST API Contract

> **Contract version:** 1
> **Status:** Authoritative

## Purpose

This document defines every version 1 application REST endpoint, its CherryPy provider, permitted caller, request/response model, status codes, query semantics, errors, and idempotency behavior. It contains no endpoint that exposes InfluxDB directly or assigns telemetry persistence to Operations Store.

## Global REST rules

- Every application-owned REST provider uses CherryPy.
- Business routes begin with `/api/v1`. Every application service also exposes `GET /health` outside that prefix.
- Paths, field names, and query names are case-sensitive.
- JSON requests use `Content-Type: application/json`; JSON responses use `Content-Type: application/json`.
- A successful request returns only the documented JSON shape. Empty success bodies are not used.
- Unknown request fields and unknown query parameters are rejected with HTTP 400.
- Paths never accept raw SQL, Flux, arbitrary URLs, filesystem paths, Python names, or MQTT wildcards.
- Timestamps and models follow [`SCHEMAS.md`](SCHEMAS.md); transitions and authorization follow [`STATES_AND_ACTIONS.md`](STATES_AND_ACTIONS.md).

## Standard headers

| Header | Direction | Required | Rule |
| --- | --- | --- | --- |
| `X-Request-ID` | Request/response | Optional request; required response | Server preserves a valid caller value or generates `req_` plus UUIDv4. It is included in every error body. |
| `X-Service-ID` | Request | Required for inter-service mutation; optional for reads and `/health` | Identifies the registered calling service. It is a logical audit/allowlist control, not production authentication. |
| `Idempotency-Key` | Request | Required for POST, incident PATCH, and action PATCH | 8–128 printable characters. For OperatorActionIntent it must equal the body `idempotency_key`. |
| `Idempotent-Replay` | Response | Present only on a replay | Literal `true` when an earlier result is returned without repeating side effects. |

Version 1 runs on a trusted local Compose network without production authentication/TLS. Mutation providers still validate `X-Service-ID` against a bounded Service Catalog cache and permit only the caller names listed below. Unknown or disallowed registered callers receive HTTP 403. This caller identity is not presented as a security boundary for Internet deployment.

## Collection and query conventions

Every collection returns:

```json
{
  "items": [],
  "count": 0
}
```

`count` is the number of objects in the current response. An endpoint accepting pagination also returns the effective `limit` and `offset`. Unless an endpoint overrides it, `limit` defaults to 100 and ranges from 1 to 500; `offset` defaults to 0 and must be non-negative. Filters combine with logical AND. Unknown filters are rejected.

Catalog collections and records without an event timestamp sort ascending by stable ID. Operational collections sort descending by their documented event timestamp (`created_at`, `observed_at`, or `processed_at`) and then by stable ID ascending. Telemetry endpoints define their own ordering. An empty valid query returns HTTP 200 with empty `items` and `count: 0`.

Time filters named `start` and `end` use an inclusive start and exclusive end against the timestamp named by that endpoint. `start` must be earlier than `end`. For telemetry this means `start <= observed_at < end`, preventing a historical detector from including the observation currently being evaluated.

## Idempotent mutation behavior

- The first valid resource-creation POST returns HTTP 201 unless its endpoint explicitly defines action-processing semantics. An identical replay returns the originally stored body with HTTP 200 and `Idempotent-Replay: true`.
- A registration that refreshes an existing identity returns HTTP 200; a new identity returns HTTP 201.
- A key is scoped to provider, endpoint, and caller service ID.
- Reusing a key with a different validated request body returns HTTP 409 `idempotency_conflict`.
- Reusing the same domain ID with different content returns HTTP 409 `resource_conflict` even when the header key differs.
- Device heartbeat/status PUTs deduplicate `heartbeat_id` or `status_event_id`. Service heartbeat/status PUTs replace the named current record, and an identical retry causes no additional domain side effect.
- Incident/action PATCH requests use both `Idempotency-Key` and the documented compare/expected-state guard.

## Error contract

Every error uses ErrorResponse:

```json
{
  "error": {
    "code": "not_found",
    "message": "Device not found",
    "details": {"device_id": "temp-lab-a-01"},
    "request_id": "req_234f720b-3df0-42d0-92a9-acfb4bd3f82e"
  }
}
```

| HTTP status | Allowed codes | Meaning |
| --- | --- | --- |
| 400 | `validation_error`, `invalid_query` | Invalid JSON, model, path/body identity, field, parameter, or time range. |
| 403 | `forbidden` | Registered caller or operator lacks authority. |
| 404 | `not_found` | Named resource does not exist. |
| 409 | `resource_conflict`, `idempotency_conflict`, `invalid_transition`, `version_conflict`, `status_conflict`, `decision_conflict` | Existing identity/content or state precondition conflicts. |
| 503 | `not_ready`, `dependency_unavailable` | Required dependency cannot be used within the bounded cache policy. |
| 500 | `internal_error` | Unexpected server failure. |

Errors contain a concise safe explanation, never a stack trace, secret, SQL/Flux text, or unbounded rejected payload.

## Health endpoint

Every service provides:

| Method and path | Caller | Response |
| --- | --- | --- |
| `GET /health` | Compose, Service Catalog, operators, tests | HealthResponse |

HTTP 200 is returned for `healthy` and `degraded`; HTTP 503 is returned for `starting`, `unavailable`, or `stopping`. The response names dependency states but contains no credentials, tokens, peer URLs, database queries, or operator data.

## Endpoint index

| Provider | Method and endpoint | Permitted caller(s) | Request | Success response |
| --- | --- | --- | --- | --- |
| Service Catalog | `POST /api/v1/services/register` | Any application service | ServiceRegistration | ServiceRecord |
| Service Catalog | `PUT /api/v1/services/<service_id>/heartbeat` | That service instance | ServiceHeartbeatRequest | ServiceRecord |
| Service Catalog | `PUT /api/v1/services/<service_id>/status` | That service instance | ServiceStatusRequest | ServiceRecord |
| Service Catalog | `GET /api/v1/services` | Application services, Dashboard | Query | CollectionResponse&lt;ServiceRecord&gt; |
| Service Catalog | `GET /api/v1/services/<service_id>` | Application services, Dashboard | None | ServiceRecord |
| Service Catalog | `GET /api/v1/services/by-name/<service_name>` | Application services | None | CollectionResponse&lt;ServiceRecord&gt; |
| Service Catalog | `GET /api/v1/tools` | Agentic AI Investigation, tests | Query | CollectionResponse&lt;ToolDescriptor&gt; |
| Service Catalog | `GET /api/v1/config/global` | Application services | None | GlobalPlatformConfig |
| Device Catalog | `POST /api/v1/devices/register` | Device Connector | DeviceRegistration | DeviceRecord |
| Device Catalog | `PUT /api/v1/devices/<device_id>/heartbeat` | Ingestion | Heartbeat | DeviceRecord |
| Device Catalog | `PUT /api/v1/devices/<device_id>/status` | Ingestion | DeviceStatusUpdate | DeviceRecord |
| Device Catalog | `GET /api/v1/devices` | Application services, Dashboard | Query | CollectionResponse&lt;DeviceRecord&gt; |
| Device Catalog | `GET /api/v1/devices/<device_id>` | Application services, Dashboard | None | DeviceRecord |
| Device Catalog | `GET /api/v1/devices/<device_id>/config` | Device Connector, Detection, Agentic AI Investigation | None | DeviceConfig |
| Device Catalog | `GET /api/v1/devices/<device_id>/actions` | Response Manager, Agentic AI Investigation | None | Allowed-action collection |
| Ingestion | `GET /api/v1/telemetry/recent` | Detection, Agentic AI Investigation, Dashboard | Query | Telemetry collection |
| Ingestion | `GET /api/v1/telemetry/window` | Detection, Agentic AI Investigation, Dashboard | Query | Telemetry collection with window |
| Ingestion | `GET /api/v1/telemetry/summary` | Detection, Agentic AI Investigation, Dashboard | Query | Summary collection with window |
| Operations Store | `POST /api/v1/alerts` | Detection | Alert | Alert |
| Operations Store | `GET /api/v1/alerts` | Detection, Agentic AI Investigation, Response Manager, Dashboard | Query | CollectionResponse&lt;Alert&gt; |
| Operations Store | `GET /api/v1/alerts/<alert_id>` | Agentic AI Investigation, Response Manager, Dashboard | None | Alert |
| Operations Store | `POST /api/v1/incidents` | Detection | Incident | Incident |
| Operations Store | `GET /api/v1/incidents` | Agentic AI Investigation, Response Manager, Dashboard | Query | CollectionResponse&lt;Incident&gt; |
| Operations Store | `GET /api/v1/incidents/<incident_id>` | Agentic AI Investigation, Response Manager, Dashboard | None | Incident |
| Operations Store | `PATCH /api/v1/incidents/<incident_id>` | Response Manager | IncidentTransitionRequest | Incident |
| Operations Store | `POST /api/v1/recommendations` | Agentic AI Investigation | Recommendation | Recommendation |
| Operations Store | `GET /api/v1/recommendations` | Agentic AI Investigation, Response Manager, Dashboard | Query | CollectionResponse&lt;Recommendation&gt; |
| Operations Store | `GET /api/v1/recommendations/<recommendation_id>` | Response Manager, Dashboard | None | Recommendation |
| Operations Store | `POST /api/v1/actions` | Response Manager | ActionRecord | ActionRecord |
| Operations Store | `PATCH /api/v1/actions/<action_id>` | Response Manager | ActionTransitionRequest | ActionRecord |
| Operations Store | `GET /api/v1/actions` | Response Manager, Dashboard | Query | CollectionResponse&lt;ActionRecord&gt; |
| Operations Store | `GET /api/v1/actions/<action_id>` | Response Manager, Dashboard | None | ActionRecord |
| Operations Store | `POST /api/v1/command-acks` | Response Manager | CommandAck | CommandAck |
| Operations Store | `GET /api/v1/command-acks` | Response Manager, Dashboard | Query | CollectionResponse&lt;CommandAck&gt; |
| Operations Store | `GET /api/v1/command-acks/<command_ack_id>` | Response Manager, Dashboard | None | CommandAck |
| Operations Store | `GET /api/v1/operators` | Response Manager, Telegram Bot | Query | CollectionResponse&lt;OperatorRecord&gt; |
| Operations Store | `POST /api/v1/operator-actions` | Response Manager | OperatorAction | OperatorAction |
| Operations Store | `GET /api/v1/operator-actions` | Response Manager, Dashboard | Query | CollectionResponse&lt;OperatorAction&gt; |
| Operations Store | `GET /api/v1/operator-actions/<operator_action_id>` | Response Manager, Dashboard | None | OperatorAction |
| Response Manager | `POST /api/v1/operator-actions` | Telegram Bot, Dashboard | OperatorActionIntent | OperatorActionResult |

## Service Catalog API

### Register a service instance

`POST /api/v1/services/register`

- Body: ServiceRegistration.
- Headers: `Idempotency-Key` required; `X-Service-ID` equals the body's `service_id` for first registration.
- New record: HTTP 201. Exact refresh of the same `service_id`, `service_name`, and `instance_id`: HTTP 200.
- A reused `service_id` with a different logical identity returns 409.
- Service Catalog sets `registered_at`, `last_seen_at`, initial `status: starting`, and `status_reason: null`.

### Record service heartbeat/status

`PUT /api/v1/services/<service_id>/heartbeat` accepts ServiceHeartbeatRequest. `X-Service-ID`, path ID, and registered identity must match. Service Catalog sets `last_seen_at` from server receipt time and returns the updated ServiceRecord.

`PUT /api/v1/services/<service_id>/status` accepts ServiceStatusRequest under the same identity rule. It updates explicit status/reason but does not copy the sender's `observed_at` into `last_seen_at`.

### Query and discover services

`GET /api/v1/services` accepts `service_name`, `status`, `capability`, `limit`, and `offset`.

`GET /api/v1/services/<service_id>` returns one record or 404.

`GET /api/v1/services/by-name/<service_name>` returns only `healthy` instances of that exact logical name, ordered by `service_id`. It returns an empty collection rather than guessing a fallback when none are healthy.

### Approved tools and global configuration

`GET /api/v1/tools` accepts optional `tool_name`, `service_name`, `limit`, and `offset`. It returns only the approved read-only ToolDescriptor values listed in [`CONFIGURATION.md`](CONFIGURATION.md). A service cannot expose a new AI tool merely by self-registration.

`GET /api/v1/config/global` returns the complete validated GlobalPlatformConfig. It contains no secret. Partial responses are forbidden.

## Device Catalog API

### Register a logical device

`POST /api/v1/devices/register`

- Body: DeviceRegistration.
- Caller: a registered `device-connector` instance named by `managed_by_service_id`.
- Device Catalog generates or validates canonical topics, validates action values and detector-profile reference syntax, and returns DeviceRecord. Detection—not Device Catalog—validates that the referenced profile definition exists.
- New device: HTTP 201. Exact idempotent refresh/update: HTTP 200.
- Reusing `device_id` for a different `device_type` or managing service returns HTTP 409.
- A configuration change increments `config_version`; a pure identical refresh does not.

### Record heartbeat and device status

`PUT /api/v1/devices/<device_id>/heartbeat` accepts Heartbeat from Ingestion only. The path/body IDs must match. Device Catalog sets `last_seen_at` from server receipt time and applies the device-state rules in [`STATES_AND_ACTIONS.md`](STATES_AND_ACTIONS.md).

`PUT /api/v1/devices/<device_id>/status` accepts DeviceStatusUpdate from Ingestion only. The path/body IDs must match. Device Catalog changes status without replacing sender `observed_at` with server time.

### Query devices and configuration

`GET /api/v1/devices` accepts `device_type`, `status`, `zone`, `managed_by_service_id`, `command_capable`, `limit`, and `offset`. The obsolete query name `type` is rejected.

`GET /api/v1/devices/<device_id>` returns DeviceRecord or 404.

`GET /api/v1/devices/<device_id>/config` returns the record's identity, resolved `settings`, canonical `topics`, command capability/whitelist, `detector_profile_id`, and `config_version`. It excludes transient liveness timestamps not needed as configuration.

`GET /api/v1/devices/<device_id>/actions` returns:

```json
{
  "device_id": "temp-lab-a-01",
  "items": ["set_safe_mode"],
  "count": 1,
  "config_version": 1
}
```

Device Catalog returns only the current executable-action whitelist. It does not return or own risk and confirmation policy; Response Manager obtains those values from its own tracked policy and intersects them with this whitelist.

## Ingestion telemetry API

These endpoints are the only application interface to historical telemetry. Ingestion alone translates them into InfluxDB operations; callers never submit or receive an InfluxDB URL, token, bucket, organization, measurement name, or Flux query.

### Recent telemetry

`GET /api/v1/telemetry/recent`

| Query | Required | Rule |
| --- | --- | --- |
| `device_id` | Yes | Existing device. |
| `metric` | No | Canonical device metric. |
| `limit` | No | Default 20; range 1–500. |

Returns NormalizedTelemetry items ordered by `observed_at` descending, then `event_id` ascending. Response includes `items`, `count`, and `limit`; no `offset` is accepted.

### Telemetry window

`GET /api/v1/telemetry/window`

| Query | Required | Rule |
| --- | --- | --- |
| `device_id` | Yes | Existing device. |
| `metric` | No | Canonical device metric. |
| `start` | Yes | Inclusive UTC timestamp. |
| `end` | Yes | Exclusive UTC timestamp later than `start`. |
| `limit` | No | Default 500; range 1–5000. |

Returns NormalizedTelemetry items ordered by `observed_at` ascending, then `event_id` ascending, plus:

```json
{
  "items": [],
  "count": 0,
  "limit": 500,
  "window": {
    "start": "2026-09-08T11:00:00Z",
    "end": "2026-09-08T12:00:00Z"
  }
}
```

If more observations match than `limit`, Ingestion returns the earliest `limit` observations in the requested window. Callers use a narrower window rather than an undocumented paging token.

### Telemetry summary

`GET /api/v1/telemetry/summary` accepts required `device_id`, required `start`/`end`, and optional `metric`. It returns one TelemetrySummary per matching metric, ordered by metric name, with the same end-exclusive `window`. Only metrics with at least one observation appear; no data returns an empty collection.

## Operations Store API

Operations Store is the SQLite-backed system of record for operational data. It has no telemetry endpoint, InfluxDB client, InfluxDB credential, or query-language passthrough. The allowed writers below are exact.

### Alerts

`POST /api/v1/alerts`

- Caller: Detection only.
- Body/response: Alert.
- Validates stable IDs, dedupe key, evidence bounds, and that the same alert/incident pair is not already associated with different content.
- Persists before Detection publishes the Alert through MQTT.

`GET /api/v1/alerts` accepts `incident_id`, `device_id`, `severity`, `detector_id`, `start`, `end`, `limit`, and `offset`. Time filters apply to `created_at` and retain end-exclusive semantics.

`GET /api/v1/alerts/<alert_id>` returns Alert or 404.

### Incidents

`POST /api/v1/incidents`

- Caller: Detection only.
- Body/response: Incident.
- New incidents must have `status: new`, `version: 1`, `current_recommendation_id: null`, and `last_action_id: null`.
- `primary_alert_id` must identify the corresponding persisted Alert and use the same `incident_id` and `device_id`.

`GET /api/v1/incidents` accepts `device_id`, `severity`, `status`, `start`, `end`, `limit`, and `offset`. Time filters apply to `created_at`.

`GET /api/v1/incidents/<incident_id>` returns Incident or 404.

`PATCH /api/v1/incidents/<incident_id>`

- Caller: Response Manager only.
- Body: IncidentTransitionRequest.
- Response: updated Incident.
- Path ID must match the existing resource. `expected_version` is compared atomically with current `version`.
- The transition must appear in [`STATES_AND_ACTIONS.md`](STATES_AND_ACTIONS.md).
- A successful transition increments `version`, sets server-derived `updated_at`, and atomically records provided recommendation/action references.
- A stale version returns HTTP 409 `version_conflict`; a forbidden state edge returns 409 `invalid_transition`.

This compare-and-swap operation is the concurrency boundary that ensures the first valid approval/rejection can win without issuing two commands.

### Recommendations

`POST /api/v1/recommendations`

- Caller: Agentic AI Investigation only.
- Body/response: Recommendation.
- Incident and every evidence reference must exist.
- Persists before the recommendation is published through MQTT.

`GET /api/v1/recommendations` accepts `incident_id`, `action`, `start`, `end`, `limit`, and `offset`. `GET /api/v1/recommendations/<recommendation_id>` returns one record or 404.

### Response actions

`POST /api/v1/actions`

- Caller: Response Manager only.
- Body/response: ActionRecord.
- A new record begins in `planned`, `awaiting_confirmation`, `issued`, `applied`, `rejected`, or `skipped` only when the corresponding policy path permits that initial status.
- `command_id` is null until a command exists and is always null for non-command outcomes.

`PATCH /api/v1/actions/<action_id>` accepts ActionTransitionRequest from Response Manager only. It checks the current `expected_status`, validates the allowed edge, applies `status`, `reason`, and optional `command_id`, and sets server-derived `updated_at` atomically. A current-status mismatch returns 409 `status_conflict`; a forbidden edge returns 409 `invalid_transition`.

`GET /api/v1/actions` accepts `incident_id`, `device_id`, `action`, `status`, `start`, `end`, `limit`, and `offset`. `GET /api/v1/actions/<action_id>` returns one record or 404.

### Command acknowledgments

`POST /api/v1/command-acks`

- Caller: Response Manager only, after receiving/validating CommandAck through MQTT.
- Body/response: CommandAck.
- The command, action, incident, and device IDs must correlate with an existing action.
- The same `command_ack_id` is idempotent; contradictory content returns 409.

`GET /api/v1/command-acks` accepts `command_id`, `action_id`, `incident_id`, `device_id`, `status`, `start`, `end`, `limit`, and `offset`. Time filters apply to `observed_at`. `GET /api/v1/command-acks/<command_ack_id>` returns one record or 404.

### Operators

`GET /api/v1/operators` accepts `operator_id`, `telegram_user_id`, `role`, `enabled`, `minimum_severity`, `limit`, and `offset`. Version 1 operator records are loaded by controlled Operations Store bootstrap/administration; there is no public operator-mutation endpoint.

Telegram Bot uses `enabled=true` and locally applies the ordered `minimum_severity` threshold. Response Manager retrieves the named operator before accepting an intent.

### Persisted operator actions

`POST /api/v1/operator-actions`

- Caller: Response Manager only.
- Body/response: OperatorAction, after policy/concurrency processing.
- Both accepted and rejected/conflicting syntactically valid intents are stored for audit.
- `operator_action_id` and `idempotency_key` cannot be reused with different content.

`GET /api/v1/operator-actions` accepts `incident_id`, `operator_id`, `action`, `accepted`, `result_code`, `start`, `end`, `limit`, and `offset`. Time filters apply to `processed_at`. `GET /api/v1/operator-actions/<operator_action_id>` returns one record or 404.

## Response Manager API

### Submit operator intent

`POST /api/v1/operator-actions`

- Callers: registered Telegram Bot or Dashboard only.
- Body: OperatorActionIntent.
- Headers: `X-Service-ID` and `Idempotency-Key` required; header key must equal body `idempotency_key`.
- Response Manager obtains the current OperatorRecord, Incident, Recommendation when required, DeviceRecord/whitelist, and response policy before deciding.
- It persists an OperatorAction for every syntactically valid intent, including losing conflicts.

For an accepted intent, HTTP 200 returns OperatorActionResult. Its `action_record` is an ActionRecord for approve/reject when one is created and is null for acknowledgment.

Behavior by action:

| Operator action | Required state/role | Effect |
| --- | --- | --- |
| `acknowledge` | Existing incident; enabled `viewer` or `operator` | Persists acknowledgment only; incident status/version does not change. |
| `approve` | `awaiting_confirmation`; enabled `operator`; current incident version/recommendation | First valid decision transitions toward command issuance; only Response Manager publishes the command. |
| `reject` | `awaiting_confirmation`; enabled `operator`; current incident version/recommendation | First valid decision rejects the ActionRecord and transitions the incident to `escalated`; no command is published. |

A later conflicting approval/rejection returns HTTP 409 `decision_conflict`. Error `details` includes `operator_action_id`, current `incident_id`, `status`, and `version` so the user-awareness client can display the authoritative result. Disabled/wrong-role operators receive 403 `forbidden`; stale incident versions receive 409 `version_conflict`; invalid states receive 409 `invalid_transition`.

## Dashboard and Telegram boundaries

- Dashboard serves its HTML/static interface with CherryPy and reads the catalogs, Ingestion, and Operations Store APIs documented here.
- Dashboard submits acknowledge/approve/reject only to Response Manager; it never writes Operations Store directly.
- Telegram Bot consumes MQTT Notification, reads enabled OperatorRecords from Operations Store, and submits operator intent only to Response Manager.
- Neither component exposes a second business-state API, accesses SQLite/InfluxDB directly, or reimplements detection/response policy.

## Provider/caller verification checklist

Before implementation proceeds, contract tests must prove:

- every endpoint is mounted on the provider named here;
- every mutation rejects a caller outside its allowlist;
- collection responses always contain `items` and `count`;
- time windows are start-inclusive/end-exclusive;
- only Ingestion's API implementation imports/uses the InfluxDB client;
- Operations Store has no telemetry endpoint;
- only Response Manager accepts operator intent and publishes commands;
- idempotent replays do not repeat persistence, transitions, publications, or command handlers; and
- every error response contains a non-secret `request_id`.
