# Smart Lab Incident Monitor — Architecture Contract

> **Contract version:** 1
> **Status:** Authoritative

## Purpose

This document defines the system's component responsibilities, ownership boundaries, permitted dependencies, and end-to-end data and control flows. Implementations must conform to these boundaries unless the contract set is versioned and updated.

## Architectural invariants

1. Ingestion is the TimeSeriesDB adaptor and the only component allowed to import, initialize, configure, authenticate to, or use an InfluxDB client.
2. Ingestion validates and normalizes incoming telemetry, writes normalized telemetry to InfluxDB, and exposes historical telemetry through CherryPy REST APIs.
3. Every other application service obtains historical telemetry through Ingestion REST APIs and must never connect directly to InfluxDB.
4. Operations Store is Influx-free, uses SQLite, and persists operational records only—not raw or normalized telemetry.
5. MQTT carries live events and commands; REST provides synchronous queries, historical lookup, configuration access, and state-changing operations.
6. Peer service addresses and non-secret shared configuration come from Service Catalog; services must not hard-code peer addresses.
7. Agentic AI Investigation may investigate and recommend actions, but only Response Manager may authorize and publish actuator commands.
8. Detection creates each alert and its initial incident; Response Manager owns subsequent incident and response-action lifecycle transitions.
9. Every application-owned REST provider uses CherryPy.

## Component responsibilities

| Component | Owns and performs | Must not own or perform |
| --- | --- | --- |
| Mosquitto | Routes application MQTT messages with the contracted QoS and retain settings. | Domain decisions or system-of-record persistence. |
| Service Catalog | Service registration, discovery, addresses, health metadata, endpoint/tool discovery, and non-secret platform configuration. | Secrets, device records, telemetry, or operational records. |
| Device Catalog | Device identity, `device_type`, configuration, generated topics, actuator capabilities, current status, server-derived `last_seen_at`, detector profile assignment, and allowed-action whitelist. | Historical telemetry, incident records, detection logic, or response authorization. |
| Device Connector | Manages logical devices; publishes raw telemetry, heartbeat, and status; consumes commands; invokes allow-listed local handlers; and publishes command acknowledgments. | Durable domain storage, anomaly detection, or final action authorization. |
| Ingestion | Validates and normalizes device messages, writes normalized telemetry to InfluxDB, publishes normalized events, serves historical telemetry, and updates Device Catalog from heartbeat/status events. | Operational-record persistence, incident reasoning, or response decisions. |
| InfluxDB | Persists normalized time-series telemetry exclusively behind Ingestion. | Acting as a cross-service API or storing operational records. |
| Detection | Consumes normalized live data, obtains history through Ingestion, applies deterministic and historical detector rules, persists the alert and initial incident, and then publishes the alert. | Direct InfluxDB access, command publication, AI investigation, or later incident lifecycle control. |
| Operations Store | Exposes CherryPy REST persistence for operational records using SQLite. | Telemetry storage, InfluxDB access, detection or AI execution, deciding lifecycle transitions, or command publication. |
| Agentic AI Investigation | Investigates alerts using approved REST-accessible context, validates and persists structured recommendations, and publishes them after persistence. | Approving actions, publishing commands, or directly changing incident state. |
| Response Manager | Applies response policy, owns later incident transitions, handles human confirmation, authorizes commands, publishes commands and notifications, and records outcomes through Operations Store. | Direct InfluxDB access, primary anomaly detection, or delegating final authorization to AI or a user-awareness service. |
| Dashboard | Presents telemetry and operational state obtained through REST and submits operator actions to Response Manager. | Direct database access, detection/policy logic, or action authorization. |
| Telegram Bot | Delivers notifications to enabled recipients and forwards authenticated operator actions to Response Manager. | Direct database access, incident mutation, policy logic, or action authorization. |

## Major data and control flows

### Normal telemetry

1. Device Connector obtains device configuration and validated topics from Device Catalog.
2. Device Connector publishes raw telemetry, heartbeat, and status through Mosquitto.
3. Ingestion validates the payload, topic identity, and registered device identity.
4. Ingestion normalizes accepted observations and updates Device Catalog from validated heartbeat/status events.
5. Ingestion writes normalized telemetry to InfluxDB.
6. Only after a successful write, Ingestion publishes the normalized event.
7. Detection consumes the normalized event.

Device Connector does not independently update device liveness through a duplicate REST path. Ingestion is the single receiver that converts MQTT heartbeat/status observations into Device Catalog updates.

### Missing-heartbeat detection

1. Device Catalog derives `stale` and `offline` from its server-observed `last_seen_at` and the device heartbeat policy.
2. Detection performs a scheduled REST query for stale/offline devices; it does not wait for a new MQTT message from a silent device.
3. Detection creates and persists the resulting alert/initial incident and follows the same incident flow as a telemetry anomaly.

### Historical telemetry retrieval

1. Detection, Agentic AI Investigation, or Dashboard discovers a healthy Ingestion instance through Service Catalog.
2. The caller requests history from Ingestion REST.
3. Ingestion translates the platform request into an InfluxDB query.
4. Ingestion returns versioned platform JSON.
5. No InfluxDB URL, credential, query language, bucket detail, or client library crosses this boundary.

### Incident and response flow

1. Detection may obtain historical context only through Ingestion REST.
2. Detection creates and persists an alert and its initial incident in Operations Store.
3. Detection publishes the persisted alert through Mosquitto.
4. Agentic AI Investigation obtains approved context through catalog and REST interfaces.
5. Agentic AI Investigation validates and persists its recommendation, then publishes it.
6. Response Manager intersects the recommendation with the device whitelist and its own response policy.
7. Response Manager records no action, performs an eligible automatic action, or enters human confirmation according to policy.
8. Only Response Manager may publish a command.
9. Device Connector validates and executes only a bounded, supported, unexpired command and publishes its acknowledgment and any resulting status.
10. Response Manager persists the resulting action and incident changes, then publishes a notification.
11. Ingestion processes a resulting device-status event and updates Device Catalog.

### User awareness and operator interaction

1. Dashboard reads telemetry and operational state through REST and sends operator intent only to Response Manager.
2. Telegram Bot consumes notifications and obtains enabled recipient records through Operations Store REST.
3. Telegram Bot delivers notifications and sends authenticated operator intent only to Response Manager REST.
4. Neither Dashboard nor Telegram Bot accesses a database directly or implements response policy.
5. Operations Store remains the REST-visible system of record for operational history.

## Authoritative ownership

Persistence ownership does not grant decision authority. The system of record and the component permitted to make domain decisions may therefore differ.

| Data or domain | System of record | Producers or decision owner | Required rule |
| --- | --- | --- | --- |
| Device metadata, configuration, and capabilities | Device Catalog | Device Connector registration; Device Catalog validation | Device Catalog generates or validates topics and allowed actions. |
| Device runtime status | Device Catalog | Ingestion updates from heartbeat/status | `last_seen_at` is receiver/server-derived. |
| Service metadata, health, and tools | Service Catalog | Each service registration/heartbeat | `service_id` identifies a service instance, not a logical device. |
| Non-secret platform configuration | Service Catalog | Service Catalog bootstrap configuration | Secrets never appear here. |
| Telemetry, history, and summaries | Ingestion | Device Connector produces raw data; Ingestion normalizes and writes | Only Ingestion accesses InfluxDB. |
| Alerts | Operations Store | Detection creates | Detection owns detection meaning; Operations Store holds authoritative history. |
| Incidents | Operations Store | Detection creates the initial record; Response Manager transitions it afterward | Response Manager owns lifecycle decisions after creation. |
| Recommendations, including bounded investigation results | Operations Store | Agentic AI Investigation | Recommendations are advisory only. |
| Response policy and authorization | Response Manager | Response Manager policy plus Device Catalog whitelist | Agentic AI Investigation, Dashboard, and Telegram Bot cannot override it. |
| Commands and action history | Operations Store | Response Manager | Stable `command_id` and `action_id` values provide correlation and logical idempotency. |
| Operators | Operations Store | Administrative/bootstrap input | A Telegram token is not operator data. |
| Operator actions | Operations Store | Response Manager validates and persists intents | Acknowledgment is not an incident state or approval. |
| Command acknowledgments | Operations Store | Device Connector emits; Response Manager persists | A command acknowledgment is distinct from human acknowledgment. |

## Enforced dependency boundaries

1. Only Ingestion receives InfluxDB credentials or uses its client.
2. Only Response Manager publishes actuator commands.
3. Services discover peer endpoints through Service Catalog.
4. No service accesses another service's persistence directly; callers use the owning service's REST APIs. Ingestion alone accesses InfluxDB, and Operations Store alone accesses its SQLite database.
5. Detection may create an alert and its initial incident but cannot perform later incident lifecycle transitions.
6. Agentic AI Investigation may recommend, and Dashboard or Telegram Bot may submit operator intent, but none may directly mutate incident/action state; only Response Manager validates and applies those transitions.
7. Catalogs contain no secrets.
8. Current state is read through REST, not reconstructed from retained MQTT messages.
9. Ingestion persists accepted telemetry before publishing its normalized event.

## Tutor correction and supersession

- Tutor correction T1, recorded from Rafael's feedback on the Ingestion and Storage service designs, established Ingestion as the TimeSeriesDB adaptor, sole InfluxDB client, and historical-telemetry REST provider.
- The former broad `Storage Service` design placed telemetry persistence between Ingestion and InfluxDB and is superseded.
- Operations Store is its deliberately narrowed successor for non-time-series operational records only.
- There is no compatibility path, alternate telemetry owner, or temporary API preserving the obsolete design.
