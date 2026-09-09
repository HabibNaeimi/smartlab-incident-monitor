# Smart Lab Incident Monitor — Contract Set

> **Contract version:** 1
> **Status:** Authoritative

## Purpose

This contract set defines the cross-service interfaces and ownership rules that must remain stable before independent service implementation continues. “Authoritative” means implementations and tests must conform to these documents; it does not prevent a controlled, versioned contract change.

## Non-negotiable architecture boundary

1. Ingestion is the TimeSeriesDB adaptor and the only application component permitted to import, initialize, configure, authenticate to, or use an InfluxDB client.
2. Ingestion writes normalized telemetry to and queries historical telemetry from InfluxDB. Every other service obtains historical telemetry through Ingestion REST APIs.
3. Operations Store is Influx-free and stores only operational records: alerts, incidents, recommendations, response actions, command acknowledgments, operators, and operator actions.
4. Every application-owned REST provider uses CherryPy. Application routes begin with `/api/v1`; every application service exposes `/health`.
5. Mosquitto carries live events and commands. REST remains authoritative for current state, configuration, discovery, and historical queries.

## Contract ownership

| Document | Authoritative for |
| --- | --- |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Component responsibilities, ownership boundaries, data flow, and control flow. |
| [`CONFIGURATION.md`](CONFIGURATION.md) | Configuration bootstrap, catalog discovery, ownership, secrets, and caching. |
| [`STATES_AND_ACTIONS.md`](STATES_AND_ACTIONS.md) | Vocabularies, lifecycle transitions, response policy, and human decisions. |
| [`SCHEMAS.md`](SCHEMAS.md) | JSON models, fields, IDs, timestamps, validation, and idempotency. |
| [`TOPICS.md`](TOPICS.md) | MQTT namespace, producers, consumers, payloads, QoS, retain, and message handling. |
| [`APIS.md`](APIS.md) | CherryPy REST endpoints, providers, callers, requests, responses, and errors. |

If these documents conflict, implementation must stop until the contract set is corrected. `ARCHITECTURE.md` owns component boundaries, while each specialized document owns its interface details. A field, topic, endpoint, state, or configuration value exists only if its owning contract defines it.

## Superseded documents

The former `freezer/` documents are historical inputs only. Historical copies may remain outside the repository for reference but must not be used as implementation authority.

| Historical document | Authoritative replacement |
| --- | --- |
| `freezer/TOPICS.md` | [`TOPICS.md`](TOPICS.md) |
| `freezer/API_CONTRACTS.md` | [`APIS.md`](APIS.md) |
| `freezer/SCHEMAS.md` | [`SCHEMAS.md`](SCHEMAS.md) |
| `freezer/ACTIONS_AND_STATES.md` | [`STATES_AND_ACTIONS.md`](STATES_AND_ACTIONS.md) |

## Change control

- All six substantive documents belong to contract version 1.
- A cross-service change must update every affected document and contract test together.
- A breaking change requires a new contract version and an explicit migration plan.
- An additive change is permitted within version 1 only when existing producers and consumers remain valid and contract tests prove compatibility.
- No authoritative document may contain an unresolved interface decision.
