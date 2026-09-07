# Smart Lab Incident Monitor

An IoT platform for smart-lab incident monitoring, investigation, and safe response. This project is being developed for the Politecnico di Torino **Programming for IoT Applications** course by Group 26.

The intended system combines simulated IoT devices, MQTT event exchange, historical time-series analysis, deterministic detection, bounded Agentic AI support, operator confirmation, a dashboard, and Telegram notifications.

## Current Status

The project is in its foundation phase. The repository currently contains:

* an initial shared Paho MQTT client helper;
* MQTT topic-construction utilities;
* Docker Compose definitions for Mosquitto 2 and InfluxDB 2;
* an authored Mosquitto configuration;
* an incomplete Device Catalog scaffold;
* a manual MQTT reconnection diagnostic;
* local environment and development dependency templates.

The following are **not yet implemented as working services**:

* Service Catalog;
* Device Catalog API;
* multi-device simulator and Device Connector;
* Ingestion and TimeSeriesDB adaptor;
* historical/statistical Detection Service;
* Operations Store;
* Agentic AI Investigation Service;
* Response Manager;
* dashboard;
* Telegram bot;
* automated unit, integration, and end-to-end tests.

The current Docker Compose file still uses legacy host bind mounts for generated broker and database state. The stack should remain stopped until these mounts are migrated to named Docker volumes and health checks are added.

## Mandatory Architecture

The final platform will follow these constraints:

* independently runnable microservices;
* CherryPy for REST API providers;
* Mosquitto as the MQTT event backbone;
* separate Device and Service Catalogs used for runtime registration and discovery;
* Ingestion as the TimeSeriesDB adaptor and the only service with direct InfluxDB access;
* REST history APIs for services that require historical telemetry;
* deterministic and historical/statistical incident detection;
* advisory Agentic AI with no direct command authority;
* Response Manager as the final policy and authorization boundary;
* mandatory Telegram-based user awareness;
* support for multiple logical devices and multiple operators.

## Local Python Setup

The currently verified development environment uses Python 3.11.

Create and activate a virtual environment if needed:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the current shared runtime dependency and development tools:

```bash
python -m pip install -r requirements-dev.txt
```

Runtime dependencies used by shared code are declared in `requirements.txt`. Development and test dependencies are declared in `requirements-dev.txt`. Future deployable services will declare their additional runtime dependencies in their own service-level `requirements.txt` files.

## Local Configuration

Create a private local environment file from the tracked template:

```bash
cp .env.example .env
```

Replace every `CHANGE_ME` value before starting infrastructure.

The real `.env` file must remain local and must never be committed or included in a source archive.

## Repository Policy

* Python caches, virtual environments, local secrets, and Docker-generated runtime state are ignored.
* Ordinary test files are not ignored.
* Reviewed architecture and interface contracts will live under `docs/contracts/`.
* Automated tests will live under `tests/`.
* Manual operational checks live under `scripts/manual/` and are not treated as automated tests.
* Generated Mosquitto databases and InfluxDB configuration/data are not application source.

## Manual MQTT Reconnection Check

The repository preserves a manual reconnection diagnostic at:

```text
scripts/manual/mqtt_reconnect_check.py
```

After the infrastructure layer is repaired and Mosquitto is running, execute it from the repository root with:

```bash
python -m scripts.manual.mqtt_reconnect_check
```

This diagnostic requires manually restarting the broker during its waiting period. It is not a pytest test and is not evidence of automated verification.
