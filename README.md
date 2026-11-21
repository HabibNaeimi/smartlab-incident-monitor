# Smart Lab Incident Monitor

An IoT platform for smart-lab incident monitoring, investigation, and safe response. This project is being developed for the Politecnico di Torino **Programming for IoT Applications** course by Group 26.

The intended system combines simulated IoT devices, MQTT event exchange, historical time-series analysis, deterministic detection, bounded Agentic AI support, operator confirmation, a dashboard, and Telegram notifications.

## Current Status

The project is in its foundation phase. The repository currently contains:

* an initial shared Paho MQTT client helper;
* MQTT topic-construction utilities;
* Docker Compose definitions for Mosquitto 2 and InfluxDB 2, with named volumes and health checks;
* an authored Mosquitto configuration;
* a validated shared bootstrap/configuration loader with scoped secrets;
* automated configuration tests and a manual import smoke check;
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
* service integration and end-to-end tests.

F01 is code verified with 198 passing configuration tests. F02 provides the
infrastructure configuration and runbook below; live Docker checks must pass in
WSL before F02 is recorded as complete.

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

Application code targets Python 3.11+. The F01 checks were run on Python 3.12.14.

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
if [ ! -f .env ]; then cp .env.example .env; fi
```

Replace every `CHANGE_ME` value before starting infrastructure.

The real `.env` file must remain local and must never be committed or included in a source archive.

Python does not automatically read `.env`. `load_config()` reads an explicit
mapping or the process environment when called at service startup. The root
template combines infrastructure examples with one example service bootstrap;
it must not be passed wholesale to every future service container.

See [configuration usage and review notes](docs/contracts/CONFIGURATION.md) for precedence,
secret ownership, startup identity, and a broker-free smoke check.

## Automated Checks

Run from the repository root, using the project environment:

```bash
python -m pytest -q tests/unit/common/config
```

F01 verification: **198 tests passed**, including the existing 112-test baseline.
Shared imports were smoke-checked manually. Live infrastructure verification is
described below; application-service integration belongs to later features.

## Local Infrastructure: F02

### What the Compose file owns

| Resource | Purpose |
| --- | --- |
| `mosquitto_data` | Broker persistence, including retained diagnostic messages. |
| `influxdb_data` | InfluxDB database files. |
| `influxdb_config` | Generated InfluxDB CLI/configuration files. |
| `smartlab` network | Shared bridge network; services resolve `mosquitto` and `influxdb` by service name. |
| Read-only `mosquitto.conf` bind mount | Authored broker configuration; generated state stays in volumes. |

The existing Mosquitto configuration already enables persistence and stdout
logging. No host log directory is mounted. Container names are assigned by
Compose, so use `docker compose exec SERVICE ...` rather than a fixed container
name. Named volumes and the network are scoped to the Compose project: keep
using the same project name and repository directory for this stack.
The configuration bind mount has `create_host_path: false`: a missing authored
file produces an error instead of silently creating a directory at that path.

Host access is limited to `127.0.0.1:1883` for MQTT and `127.0.0.1:8086` for
InfluxDB. Application containers on the bridge use `mosquitto:1883` and
`http://influxdb:8086`. Anonymous, unencrypted MQTT is intended for this trusted
local demo. The existing major-version image tags are retained; this change is
not an image upgrade or a digest-locked release.

### Preserve existing data before changing mounts

Run the following with the OLD Compose file, before applying the F02 edit:

```bash
docker compose images
docker compose stop --timeout 30
docker compose down
```

Keep the existing `infra/mosquitto/data`, `infra/influxdb/data`, and
`infra/influxdb/config` directories. Ordinary `down` does not delete those bind
directories. The new named volumes start separately; old files are not copied
automatically. Keep your existing private `.env` and any backup outside Git.
Do not use `down -v`: it deletes named volumes.

If no old runtime data is needed, continue to startup below. If old data must
be reused, follow the optional copy procedure after editing the Compose file
and before the FIRST startup with the new mounts:

```bash
docker compose run --rm --no-deps --pull never --user 0 --entrypoint sh \
  -v "$PWD/infra/mosquitto/data:/legacy:ro" \
  mosquitto -c 'cp -a /legacy/. /mosquitto/data/'

docker compose run --rm --no-deps --pull never --user 0 --entrypoint sh \
  -v "$PWD/infra/influxdb/data:/legacy-data:ro" \
  -v "$PWD/infra/influxdb/config:/legacy-config:ro" \
  influxdb -c 'cp -a /legacy-data/. /var/lib/influxdb2/ && cp -a /legacy-config/. /etc/influxdb2/'
```

These copy commands require the listed old directories to exist and the new
volumes to be unused. Run only the block for a service whose old data must be
kept. Copy both InfluxDB directories together. The old sources
are mounted read-only; container root handles their existing file permissions.
Keep the old database's credentials and image version when migrating; do not
pull a newer image as part of a raw directory copy. `--pull never` requires the
existing local images. Record the old image IDs before stopping the stack.
Preserve the old files until
the copied data has been verified. An initialized new database must not be
merged with old database files.

### Start and observe readiness

Docker must be available in WSL, with Compose supporting `up --wait` and
`--wait-timeout`. Check `docker info` and `docker compose version` first.
Create `.env` only if absent, and replace its two infrastructure `CHANGE_ME`
values. `openssl rand -hex 32` can generate a local token. Do not print or share
the real `.env`, rendered environment values, or generated `influx-configs`.

```bash
docker compose config --quiet
docker compose up -d --wait --wait-timeout 120
docker compose ps
```

Both services should show `healthy`. Running means the container process exists;
healthy means its protocol check succeeded. Mosquitto's check publishes an empty
QoS 1 message and waits for its acknowledgment. InfluxDB's check calls its HTTP
health endpoint through `influx ping`. Compose waits at most 120 seconds for
readiness; an error is not a successful startup.

Confirm InfluxDB setup and authenticated access to the configured bucket:

```bash
curl --fail --silent --show-error http://127.0.0.1:8086/api/v2/setup

docker compose exec -T influxdb sh -c '
  export INFLUX_TOKEN="$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN"
  influx bucket list --host http://127.0.0.1:8086 \
    --org "$DOCKER_INFLUXDB_INIT_ORG" --name "$DOCKER_INFLUXDB_INIT_BUCKET"
'
```

The first response should contain `"allowed":false`; the second should list
the bucket named in `.env` (normally `telemetry`). These are infrastructure CLI
checks; application access to InfluxDB still belongs only to Ingestion.

### Verify MQTT and persistence

Publish a retained diagnostic message, then receive it using a separate client:

```bash
docker compose exec -T mosquitto mosquitto_pub \
  -h mosquitto -t healthcheck/f02 -m f02-persistence-ok -q 1 -r
docker compose exec -T mosquitto mosquitto_sub \
  -h mosquitto -t healthcheck/f02 -q 1 -C 1 -W 10
```

Expected output: `f02-persistence-ok`. The `healthcheck/` prefix is reserved here
for infrastructure diagnostics, outside the application telemetry contracts.
The retained flag is for this persistence check, not a telemetry default.

Write one infrastructure test point and query it using the Influx CLI:

```bash
printf 'infra_smoke,source=f02 value=1i\n' | docker compose exec -T influxdb sh -c '
  export INFLUX_TOKEN="$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN"
  influx write --host http://127.0.0.1:8086 \
    --org "$DOCKER_INFLUXDB_INIT_ORG" --bucket "$DOCKER_INFLUXDB_INIT_BUCKET"
'

docker compose exec -T influxdb sh -c '
  export INFLUX_TOKEN="$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN"
  influx query --host http://127.0.0.1:8086 --org "$DOCKER_INFLUXDB_INIT_ORG" \
    "from(bucket: \"$DOCKER_INFLUXDB_INIT_BUCKET\") |> range(start: -24h) |> filter(fn: (r) => r._measurement == \"infra_smoke\" and r.source == \"f02\") |> last()"
'
```

Expect a result for `infra_smoke`, source `f02`, with field `value` equal to `1`.
This test measurement is separate from the future normalized telemetry schema.

Now remove the containers and recreate them while retaining the volumes:

```bash
docker compose down
docker compose up -d --wait --wait-timeout 120
docker compose ps
```

Repeat the MQTT SUBSCRIBE command and the Influx QUERY command above, without
publishing or writing again. Both previous results must still be present.
This proves persistence across container removal/recreation, not merely a new
write after restart. Clear the retained diagnostic message after verification:

```bash
docker compose exec -T mosquitto mosquitto_pub -h mosquitto -t healthcheck/f02 -q 1 -r -n
```

For normal shutdown, use `docker compose stop` to keep containers or
`docker compose down` to remove containers and the network. Both retain named
volumes. Do not add `-v` to the normal shutdown command.

### Failures and completion evidence

If a startup or protocol check fails, stop at that step and inspect:

```bash
docker compose ps -a
docker compose logs --tail 80 mosquitto influxdb
```

Review output locally before sharing it. A missing required `.env` value fails
Compose validation by variable name. A timeout requires inspecting the service
health/logs; deleting volumes is not a repair step. After initial database
creation, changing initialization credentials in `.env` does not change the
database's existing credentials.

F02 completion requires successful Compose validation, healthy services, setup
and bucket checks, MQTT delivery, an InfluxDB write/query, and the same data
after `down`/`up` without deleting volumes. The prepared configuration is checked
offline; these live Docker outcomes must be recorded from WSL. Existing Python
configuration tests should remain at 198 passed. The next feature is F03,
the first CherryPy Service Catalog.

References: [Compose readiness](https://docs.docker.com/reference/cli/docker/compose/up/),
[Docker volumes](https://docs.docker.com/engine/storage/volumes/),
[InfluxDB health](https://docs.influxdata.com/influxdb/v2/reference/cli/influx/ping/),
and [MQTT subscriber options](https://mosquitto.org/man/mosquitto_sub-1.html).

## Repository Policy

* Python caches, virtual environments, local secrets, and Docker-generated runtime state are ignored.
* Ordinary test files are not ignored.
* Reviewed architecture and interface contracts live under `docs/contracts/`.
* Automated tests live under `tests/`.
* Manual operational checks live under `scripts/manual/` and are not treated as automated tests.
* Generated Mosquitto databases and InfluxDB configuration/data are not application source.

## Manual MQTT Reconnection Check

The repository preserves a manual reconnection diagnostic at:

```text
scripts/manual/mqtt_reconnect_check.py
```

After F02 startup succeeds, execute it from the repository root with:

```bash
python -m scripts.manual.mqtt_reconnect_check
```

This diagnostic requires manually restarting the broker during its waiting period. It is not a pytest test and is not evidence of automated verification.
