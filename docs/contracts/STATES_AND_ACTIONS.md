# Smart Lab Incident Monitor — States and Actions Contract

> **Contract version:** 1
> **Status:** Authoritative

## Purpose

This document defines the exact domain vocabularies, state meanings, permitted transitions, response policy, command-safety rules, and multi-operator decision semantics. Values are lowercase snake case and are serialized exactly as written.

## Frozen vocabularies

| Vocabulary | Allowed values |
| --- | --- |
| Device status | `online`, `offline`, `stale`, `degraded`, `safe_mode`, `isolated`, `maintenance` |
| Service status | `starting`, `healthy`, `degraded`, `unavailable`, `stopping` |
| Incident status | `new`, `under_investigation`, `awaiting_confirmation`, `mitigation_in_progress`, `mitigated`, `escalated`, `closed` |
| Severity | `info`, `low`, `medium`, `high`, `critical` |
| Recommendation/action | `notify_operator_only`, `increase_monitoring`, `set_safe_mode`, `logical_isolation`, `no_immediate_action` |
| Action risk | `low`, `medium`, `high` |
| Action status | `planned`, `awaiting_confirmation`, `issued`, `applied`, `rejected`, `failed`, `timed_out`, `skipped` |
| Command acknowledgment status | `received`, `applied`, `rejected`, `failed` |
| Operator action | `acknowledge`, `approve`, `reject` |
| Operator role | `viewer`, `operator` |
| Telemetry quality | `ok`, `suspect` |
| Notification kind | `alert_created`, `confirmation_required`, `action_issued`, `action_applied`, `action_rejected`, `action_failed`, `action_timed_out`, `incident_escalated`, `incident_closed` |

An implementation must reject an unknown value rather than map it silently to a known value. Extending any vocabulary is a cross-service contract change.

Telemetry quality `ok` means the observation passed schema/device validation while the device was not degraded. `suspect` means the observation remains valid and is still persisted/published, but Device Catalog reported the device as `degraded` at ingestion time. Quality is not an anomaly decision; Detection still evaluates the observation under its profile.

## Severity ordering

Severity is ordered from least to most urgent:

```text
info < low < medium < high < critical
```

This ordering is used only for filtering, routing, and escalation. It does not independently authorize a device command; action authorization comes from the response policy and device whitelist.

## Device status semantics

| Status | Meaning |
| --- | --- |
| `online` | Heartbeat is current and the device reports normal operation. |
| `offline` | No usable heartbeat has been observed for twice the configured stale interval, or the device explicitly reports shutdown. |
| `stale` | The last server-observed heartbeat age exceeds `stale_after_s` but does not yet exceed twice that interval. |
| `degraded` | The device remains reachable but reports reduced capability or invalid operating conditions. |
| `safe_mode` | A bounded `set_safe_mode` command was applied and the device remains reachable in its restricted mode. |
| `isolated` | A bounded `logical_isolation` command was applied. |
| `maintenance` | The device is intentionally excluded from normal monitoring by controlled local configuration. |

Device Catalog owns the current device status. Ingestion is the only service that writes observed heartbeat/status updates to Device Catalog. `last_seen_at` is set using Device Catalog server time; sender-provided `observed_at` never replaces it.

Heartbeat processing may restore `offline`, `stale`, or `degraded` to `online`. A heartbeat alone must not clear `safe_mode`, `isolated`, or `maintenance`; clearing those states requires a validated device status event resulting from an authorized/local administrative operation.

`under_investigation`, `awaiting_confirmation`, and `quarantined` are not device statuses. Investigation and confirmation belong to incident workflow; version 1 represents isolation with `isolated`.

## Service status semantics

| Status | Meaning |
| --- | --- |
| `starting` | Process is running but required configuration or dependencies are not ready. |
| `healthy` | Required local checks and dependencies are ready. |
| `degraded` | Core service remains usable with a bounded impairment, such as a last-known-good catalog cache. |
| `unavailable` | Required work cannot be accepted or the service heartbeat exceeded the configured stale interval. |
| `stopping` | Graceful shutdown has begun and new work is no longer accepted. |

A service starts as `starting`, becomes `healthy` only after readiness checks, and reports `stopping` before graceful exit when possible. Service Catalog derives liveness from server receipt time and marks a record `unavailable` when no heartbeat arrives within `stale_after_s`. A new valid heartbeat may restore an unavailable instance to its explicitly reported `healthy` or `degraded` state.

## Incident lifecycle ownership

- Detection allocates `alert_id` and `incident_id`, persists the alert, and creates the incident in `new`.
- Response Manager is the only component permitted to change incident status after creation.
- Operations Store enforces the transition table and optimistic version check but does not decide which transition to request.
- Agentic AI Investigation, Dashboard, and Telegram Bot never mutate incident status directly.

## Incident transition table

Every accepted transition increments the incident's integer `version` by one and sets server-derived `updated_at`. A request naming the current status as its target is an idempotent no-op only when its idempotency key matches the previously accepted request; otherwise it is rejected as an invalid transition.

| From | To | Required trigger | Authorized requester |
| --- | --- | --- | --- |
| `new` | `under_investigation` | Response Manager accepts the persisted alert and starts bounded investigation. | Response Manager |
| `new` | `escalated` | Investigation cannot safely begin or a required deterministic dependency is unavailable. | Response Manager |
| `under_investigation` | `awaiting_confirmation` | A validated executable recommendation requires human confirmation. | Response Manager |
| `under_investigation` | `mitigation_in_progress` | An automatically authorized executable command is issued. | Response Manager |
| `under_investigation` | `escalated` | Policy selects notification-only handling, no safe action exists, or investigation fails. | Response Manager |
| `under_investigation` | `closed` | Policy validates `no_immediate_action` and records the reason. | Response Manager |
| `awaiting_confirmation` | `mitigation_in_progress` | The first valid approval wins and the corresponding command is issued. | Response Manager |
| `awaiting_confirmation` | `escalated` | The action is rejected, confirmation expires, or command issuance cannot proceed safely. | Response Manager |
| `mitigation_in_progress` | `mitigated` | Device Connector reports an `applied` command acknowledgment. | Response Manager |
| `mitigation_in_progress` | `escalated` | Device Connector reports `rejected`/`failed`, or the command times out without an allowed retry. | Response Manager |
| `mitigated` | `closed` | Resolution evidence is recorded and Response Manager closes the incident. | Response Manager |
| `escalated` | `closed` | Manual resolution or an explicit no-further-action decision is recorded. | Response Manager |

`closed` is terminal. A recurrence creates a new alert and incident rather than reopening the closed record. `mitigated` means the commanded mitigation succeeded; it is not terminal until resolution is confirmed and the incident is closed.

## Minimum response policy

Response Manager computes authorization from this table. Agentic AI Investigation's `requires_confirmation` field is a hint that must be validated against this policy and cannot weaken it.

| Action | Risk | Device command | Authorization | Action result before/without command | Incident result |
| --- | --- | --- | --- | --- | --- |
| `notify_operator_only` | `low` | No | Automatic | `applied` after notification publication is locally accepted | `escalated` |
| `increase_monitoring` | `low` | Yes | Automatic only when the device whitelist and capability permit it | `issued` when the command is committed for publication | `mitigation_in_progress` |
| `set_safe_mode` | `medium` | Yes | Human confirmation required | `awaiting_confirmation`, then `issued` after approval | `awaiting_confirmation`, then `mitigation_in_progress` |
| `logical_isolation` | `high` | Yes | Human confirmation required | `awaiting_confirmation`, then `issued` after approval | `awaiting_confirmation`, then `mitigation_in_progress` |
| `no_immediate_action` | `low` | No | Automatic | `skipped` with a recorded reason | `closed` |

An executable recommendation is rejected when the target device is not command-capable, the action is absent from its current whitelist, its parameter object is invalid, or no local handler exists. The ActionRecord becomes `rejected`, and the incident becomes `escalated`; no command is published.

## Action parameters

Unknown parameters are rejected. The version 1 parameter contracts are:

| Action | Exact parameter object |
| --- | --- |
| `notify_operator_only` | Empty object `{}`. |
| `increase_monitoring` | `telemetry_interval_s`: integer 1–60; `duration_s`: integer 60–3600. No other fields. |
| `set_safe_mode` | Empty object `{}`. |
| `logical_isolation` | Empty object `{}`. |
| `no_immediate_action` | Empty object `{}`. |

Only `increase_monitoring`, `set_safe_mode`, and `logical_isolation` may appear in a `Command`.

## Action lifecycle

| From | To | Trigger |
| --- | --- | --- |
| `planned` | `awaiting_confirmation` | Policy requires approval. |
| `planned` | `issued` | An automatic executable action passes all checks and its command is committed for publication. |
| `planned` | `applied` | A non-command notification action completes. |
| `planned` | `failed` | A non-command notification cannot be published after its bounded retry policy. |
| `planned` | `skipped` | `no_immediate_action` is selected and the reason is recorded. |
| `planned` | `rejected` | Policy, whitelist, capability, or parameter validation refuses the action. |
| `awaiting_confirmation` | `issued` | First valid approval wins and the command is committed for publication. |
| `awaiting_confirmation` | `rejected` | First valid rejection wins. |
| `awaiting_confirmation` | `timed_out` | Confirmation deadline expires. |
| `issued` | `applied` | A terminal `applied` CommandAck is persisted. |
| `issued` | `rejected` | A terminal `rejected` CommandAck is persisted. |
| `issued` | `failed` | Local command publication fails after commit, or a terminal `failed` CommandAck is persisted. |
| `issued` | `timed_out` | Command expiry passes without a terminal acknowledgment and no policy retry remains. |

`applied`, `rejected`, `failed`, `timed_out`, and `skipped` are terminal ActionRecord statuses. A `received` CommandAck confirms receipt but leaves the action in `issued`. Duplicate acknowledgments do not repeat a transition.

## Operator permissions and decisions

| Role | `acknowledge` | `approve` | `reject` |
| --- | --- | --- | --- |
| `viewer` | Allowed | Forbidden | Forbidden |
| `operator` | Allowed | Allowed | Allowed |

An operator must be enabled. `minimum_severity` controls notification routing only and grants no additional permission.

### Acknowledgment

- `acknowledge` records that an operator saw an incident.
- It is an immutable OperatorAction record and does not change incident or ActionRecord state.
- It never means `approve` and never satisfies human confirmation.
- Multiple enabled operators may independently acknowledge the same incident.

### Approval and rejection

An `approve` or `reject` intent is valid only when all conditions hold:

1. The operator exists, is enabled, and has role `operator`.
2. The incident is currently `awaiting_confirmation`.
3. The intent references the current recommendation and current incident `version`.
4. The supplied idempotency key has not been reused for a different request.
5. The action remains command-capable, whitelisted, unexpired, and valid under current policy.

The first valid `approve` or `reject` is committed through an optimistic compare-and-set on incident `version`. A duplicate of the winning intent returns the stored result without repeating side effects. Every later conflicting attempt is persisted with `accepted: false` and result code `conflict`, returns HTTP 409, and cannot publish another command.

## Command safety and acknowledgment

Only Response Manager constructs and publishes a `Command`. Before publication it validates the current device record, allowed-action whitelist, action parameters, confirmation result, incident version, and expiry.

Device Connector performs all of these checks again:

- topic `device_id` equals payload `device_id`;
- target device is managed locally and is command-capable;
- action is in the current device whitelist and has a specific local handler;
- parameters exactly match the selected action contract;
- current time is earlier than `expires_at`;
- `command_id` has not already been executed.

An accepted command produces a `received` acknowledgment before execution and exactly one terminal `applied` or `failed` acknowledgment afterward. A command rejected before execution produces exactly one terminal `rejected` acknowledgment. A duplicate command is not executed again; Device Connector republishes the previously stored terminal acknowledgment with the same `command_ack_id`.

Response Manager persists acknowledgments idempotently. `applied` moves the corresponding action to `applied`; `rejected` and `failed` move it to the matching terminal status. Expiry without a terminal acknowledgment produces `timed_out`. Human acknowledgment and command acknowledgment are unrelated record types.

## Notification rules

- Response Manager is the only producer of application notifications.
- Required ActionRecord/Incident state is persisted before a confirmation-required Notification is published and Response Manager waits for operator intent.
- Notification is a transient MQTT event, not an Operations Store record; the related Incident, ActionRecord, and OperatorAction provide durable audit state.
- Notifications contain no Telegram chat IDs, bot tokens, database credentials, or LLM secrets.
- Telegram Bot resolves enabled recipients from Operations Store and applies `minimum_severity` using the defined severity order.
- Dashboard reads the same authoritative incident/action state through REST; it does not infer state from notification delivery.
