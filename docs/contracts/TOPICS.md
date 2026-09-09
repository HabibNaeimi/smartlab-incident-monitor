# Smart Lab Incident Monitor — MQTT Topic Contract

> **Contract version:** 1
> **Status:** Authoritative

## Purpose

This document defines the exact MQTT namespace, topic ownership, payload models, QoS, retain behavior, subscriptions, validation, idempotency, and reconnect behavior. MQTT is the live event/control plane; current state and history are obtained through REST.

## Namespace

The version 1 namespace is:

```text
smartlab/<site>/...
```

For the project demonstration:

- root is exactly `smartlab` in lowercase;
- site is exactly `polito-smartlab`;
- topics have no leading or trailing slash;
- generated topic segments are lowercase; and
- a dynamic identifier must not contain `/`, `+`, or `#`.

Only trusted subscription helpers may insert MQTT wildcards. A caller-provided device ID, site ID, or other dynamic value containing a wildcard is rejected before topic construction.

## Authoritative topic table

All payloads are UTF-8 JSON matching the named model in [`SCHEMAS.md`](SCHEMAS.md).

| Topic pattern | Sole producer | Consumer(s) | Payload | QoS | Retain |
| --- | --- | --- | --- | --- | --- |
| `smartlab/<site>/devices/<device_id>/telemetry` | Device Connector | Ingestion | RawTelemetry | 0 | false |
| `smartlab/<site>/devices/<device_id>/heartbeat` | Device Connector | Ingestion | Heartbeat | 1 | false |
| `smartlab/<site>/devices/<device_id>/status` | Device Connector | Ingestion | DeviceStatusUpdate | 1 | false |
| `smartlab/<site>/devices/<device_id>/cmd` | Response Manager | Device Connector | Command | 1 | false |
| `smartlab/<site>/devices/<device_id>/ack` | Device Connector | Response Manager | CommandAck | 1 | false |
| `smartlab/<site>/normalized/<device_id>/telemetry` | Ingestion | Detection | NormalizedTelemetry | 0 | false |
| `smartlab/<site>/normalized/<device_id>/heartbeat` | Ingestion | Detection when a liveness profile consumes it | Heartbeat | 1 | false |
| `smartlab/<site>/normalized/<device_id>/status` | Ingestion | Detection when a status-aware profile consumes it | DeviceStatusUpdate | 1 | false |
| `smartlab/<site>/alerts` | Detection | Agentic AI Investigation, Response Manager | Alert | 1 | false |
| `smartlab/<site>/recommendations` | Agentic AI Investigation | Response Manager | Recommendation | 1 | false |
| `smartlab/<site>/notifications` | Response Manager | Telegram Bot | Notification | 1 | false |

No application message is retained. A new/restarted consumer reconstructs current state from the owning REST API rather than treating the latest broker message as state.

## Canonical demo topics

For device `temp-lab-a-01`, the canonical topics are:

```text
smartlab/polito-smartlab/devices/temp-lab-a-01/telemetry
smartlab/polito-smartlab/devices/temp-lab-a-01/heartbeat
smartlab/polito-smartlab/devices/temp-lab-a-01/status
smartlab/polito-smartlab/devices/temp-lab-a-01/cmd
smartlab/polito-smartlab/devices/temp-lab-a-01/ack
smartlab/polito-smartlab/normalized/temp-lab-a-01/telemetry
smartlab/polito-smartlab/normalized/temp-lab-a-01/heartbeat
smartlab/polito-smartlab/normalized/temp-lab-a-01/status
```

The site-wide event topics are:

```text
smartlab/polito-smartlab/alerts
smartlab/polito-smartlab/recommendations
smartlab/polito-smartlab/notifications
```

Topic matching is byte-for-byte and case-sensitive. `smartLab`, `polito`, and alternative pluralizations are not aliases.

## Subscription table

| Consumer | Subscription filter(s) | QoS |
| --- | --- | --- |
| Ingestion | `smartlab/<site>/devices/+/telemetry` | 0 |
| Ingestion | `smartlab/<site>/devices/+/heartbeat` | 1 |
| Ingestion | `smartlab/<site>/devices/+/status` | 1 |
| Detection | `smartlab/<site>/normalized/+/telemetry` | 0 |
| Detection | `smartlab/<site>/normalized/+/heartbeat` when required by configured profiles | 1 |
| Detection | `smartlab/<site>/normalized/+/status` when required by configured profiles | 1 |
| Agentic AI Investigation | `smartlab/<site>/alerts` | 1 |
| Response Manager | `smartlab/<site>/alerts` | 1 |
| Response Manager | `smartlab/<site>/recommendations` | 1 |
| Response Manager | `smartlab/<site>/devices/+/ack` | 1 |
| Device Connector | One concrete `.../cmd` topic for each logical device it currently manages | 1 |
| Telegram Bot | `smartlab/<site>/notifications` | 1 |

Dashboard has no MQTT subscription in version 1; it uses REST polling.

## Common topic-helper interface

The shared topic module constructs every application topic. It accepts explicit validated configuration rather than reading environment variables at import time. The required logical helpers are:

```python
raw_telemetry(device_id, *, site_id, root)
raw_heartbeat(device_id, *, site_id, root)
raw_status(device_id, *, site_id, root)
device_cmd(device_id, *, site_id, root)
device_ack(device_id, *, site_id, root)
normalized_telemetry(device_id, *, site_id, root)
normalized_heartbeat(device_id, *, site_id, root)
normalized_status(device_id, *, site_id, root)
alerts(*, site_id, root)
recommendations(*, site_id, root)
notifications(*, site_id, root)
all_raw_telemetry(*, site_id, root)
all_raw_heartbeat(*, site_id, root)
all_raw_status(*, site_id, root)
all_normalized_telemetry(*, site_id, root)
all_normalized_heartbeat(*, site_id, root)
all_normalized_status(*, site_id, root)
```

These signatures describe the shared interface, not an implementation requirement to use positional arguments. `site_id` and `root` are injected from validated configuration. Device Catalog uses only concrete-device helpers when generating records; wildcard helpers are for trusted subscribers only.

## Publication ordering

The following order is mandatory:

1. Ingestion validates and writes an accepted normalized observation to InfluxDB before publishing NormalizedTelemetry.
2. Detection persists Alert and the initial Incident in Operations Store before publishing Alert.
3. Agentic AI Investigation persists Recommendation in Operations Store before publishing Recommendation.
4. Response Manager persists the ActionRecord and required Incident transition before publishing a Command.
5. Response Manager persists CommandAck-driven ActionRecord/Incident updates before publishing the corresponding Notification.

If required persistence fails, the dependent publication does not occur. The service reports a bounded dependency failure rather than publishing an event that refers to missing authoritative state.

## Payload and topic validation

Every subscriber performs validation before domain processing:

1. Decode bytes as UTF-8.
2. Parse one JSON object.
3. Validate `schema_version` and the named shared model.
4. Parse the topic using the canonical helper/parser.
5. When the topic contains `device_id`, require byte-for-byte equality with the payload's `device_id`.
6. Require the topic site to equal the configured site.
7. For device-originated events, confirm the device exists in Device Catalog.
8. Apply idempotency before causing a second side effect.

An event for an unknown device is rejected and counted. Telemetry never auto-registers a device. A malformed/unknown message is dropped, logged with topic, safe object ID when available, and validation reason, and counted without crashing the MQTT callback or network thread. Logs do not contain secrets or an unbounded raw payload.

## QoS and idempotency

QoS 0 telemetry may be lost and is not retransmitted by application code. It is suitable for periodic sensor observations because later samples continue the stream.

Every QoS 1 consumer is logically idempotent:

| Payload | Idempotency field |
| --- | --- |
| Heartbeat | `heartbeat_id` |
| DeviceStatusUpdate | `status_event_id` |
| Alert | `alert_id` |
| Recommendation | `recommendation_id` |
| Command | `command_id` |
| CommandAck | `command_ack_id` |
| Notification | `notification_id` |

A duplicate ID with identical content reuses the original result and causes no repeated state transition, command execution, or notification delivery. Reusing an ID with different content is a conflict and is rejected/logged. Idempotency state for durable domain records is recovered from Operations Store after restart.

MQTT ordering is relied on only within one client connection and topic. Cross-topic consumers correlate by stable IDs and must not assume global ordering.

## Command and acknowledgment behavior

- Only Response Manager publishes to a `/cmd` topic.
- Response Manager obtains the concrete command topic from the current Device Catalog record.
- Device Connector subscribes only to the concrete command topics of devices it manages.
- Command expiry, whitelist, capability, parameters, topic/body identity, and deduplication are validated before execution.
- A valid command is handled only by a local bounded function; payload values cannot select arbitrary Python functions, tools, shell commands, or URLs.
- Device Connector publishes acknowledgment events on the same device's `/ack` topic according to [`STATES_AND_ACTIONS.md`](STATES_AND_ACTIONS.md).
- Response Manager persists each acknowledgment and never treats a command acknowledgment as a human acknowledgment.

## MQTT client behavior

- Each simultaneous client has a unique ID in the form `smartlab-<service_name>-<instance_suffix>`.
- `service_name` and `instance_suffix` are lowercase/topic-safe; the final client ID is no more than 128 characters.
- Version 1 uses clean session `true` and no retained application messages.
- A client retries initial connection with bounded backoff, reconnects after disconnection, and resubscribes to its complete validated subscription set after reconnect.
- A publisher checks the Paho publish result. A non-success result is recorded and exposed through logs/health; code must not report a publication as successful merely because `publish()` returned.
- MQTT callbacks perform bounded decode/validation/dispatch work and hand longer domain work to service-controlled processing; malformed input must not terminate the network loop.
- Authentication/TLS may be added later without changing topic or payload contracts. Version 1 uses the trusted local Compose network configured in [`CONFIGURATION.md`](CONFIGURATION.md).

## Explicitly excluded topics

Version 1 defines no topic for:

- historical queries or current-state reads;
- direct writes to InfluxDB or Operations Store;
- operator approval/rejection—the controlled intent uses Response Manager REST;
- dashboard updates;
- service registration/discovery; or
- arbitrary AI tools/actions.

No obsolete `smartLab/...`, `.../incidents/...`, separate actuator namespace, or telemetry-to-Operations-Store topic is accepted as an alias.
