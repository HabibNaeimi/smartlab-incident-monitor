from common.config.loader import _read_bootstrap_file, _resolve_bootstrap, load_config
from common.config.env import ConfigurationError
from common.config.settings import ServiceBootstrap
from uuid import UUID
import pytest
import json

@pytest.mark.parametrize(
    "payload",
    [
        {
            "SERVICE_NAME": "monitor",
            "INSTANCE_ID": "monitor-01",
            "BASE_URL": "http://localhost:8080",
            "SERVICE_CATALOG_URL": "http://localhost:8081",
        },
        {"SERVICE_NAME": " monitor "},
        {},
    ],
    ids=["complete", "partial", "empty"],
)
def test_read_bootstrap_file_accepts_valid_objects(tmp_path, payload):
    path = tmp_path / "bootstrap.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert _read_bootstrap_file(path) == payload


@pytest.mark.parametrize(
    "key",
    ["EXTRA_KEY", "INFLUXDB_TOKEN", "SERVICE_BOOTSTRAP_PATH"],
)
def test_read_bootstrap_file_rejects_unsupported_keys(tmp_path, key):
    path = tmp_path / "bootstrap.json"
    payload = {"SERVICE_NAME": "monitor", key: "unexpected"}
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ConfigurationError):
        _read_bootstrap_file(path)


@pytest.mark.parametrize(
    "value",
    [123, 1.5, True, None, ["monitor"], {"name": "monitor"}],
    ids=["integer", "float", "boolean", "null", "array", "object"],
)
def test_read_bootstrap_file_rejects_non_string_values(tmp_path, value):
    path = tmp_path / "bootstrap.json"
    path.write_text(json.dumps({"SERVICE_NAME": value}), encoding="utf-8")

    with pytest.raises(ConfigurationError):
        _read_bootstrap_file(path)


def test_read_bootstrap_file_rejects_json_array(tmp_path):
    path = tmp_path / "bootstrap.json"
    path.write_text(json.dumps(["monitor"]), encoding="utf-8")

    with pytest.raises(ConfigurationError):
        _read_bootstrap_file(path)


def test_read_bootstrap_file_rejects_malformed_json(tmp_path):
    path = tmp_path / "bootstrap.json"
    path.write_text('{"SERVICE_NAME": "monitor",}', encoding="utf-8")

    with pytest.raises(ConfigurationError):
        _read_bootstrap_file(path)


def test_read_bootstrap_file_rejects_missing_file(tmp_path):
    path = tmp_path / "missing.json"

    with pytest.raises(ConfigurationError):
        _read_bootstrap_file(path)


@pytest.fixture
def bootstrap_values():
    return {
        "SERVICE_NAME": "ingestion",
        "INSTANCE_ID": "ingestion-01",
        "BASE_URL": "http://ingestion:8080",
        "SERVICE_CATALOG_URL": "http://service-catalog:8080",
    }


def test_resolve_bootstrap_from_environment(bootstrap_values):
    source = {name: f" {value} " for name, value in bootstrap_values.items()}

    assert _resolve_bootstrap(source) == ServiceBootstrap(
        service_name="ingestion",
        instance_id="ingestion-01",
        base_url="http://ingestion:8080",
        service_catalog_url="http://service-catalog:8080",
    )


def test_resolve_bootstrap_from_file_only(tmp_path, bootstrap_values):
    path = tmp_path / "bootstrap.json"
    path.write_text(json.dumps(bootstrap_values), encoding="utf-8")

    assert _resolve_bootstrap({"SERVICE_BOOTSTRAP_PATH": str(path)}) == (
        _resolve_bootstrap(bootstrap_values)
    )


def test_resolve_bootstrap_completes_partial_file(tmp_path, bootstrap_values):
    path = tmp_path / "bootstrap.json"
    path.write_text('{"SERVICE_NAME": "ingestion"}', encoding="utf-8")
    source = {**bootstrap_values, "SERVICE_BOOTSTRAP_PATH": str(path)}
    del source["SERVICE_NAME"]

    assert _resolve_bootstrap(source).service_name == "ingestion"
    assert _resolve_bootstrap(source).instance_id == "ingestion-01"


def test_resolve_bootstrap_environment_overrides_file(tmp_path, bootstrap_values):
    path = tmp_path / "bootstrap.json"
    path.write_text(json.dumps(bootstrap_values), encoding="utf-8")
    source = {
        "SERVICE_BOOTSTRAP_PATH": str(path),
        "INSTANCE_ID": " ingestion-02 ",
        "BASE_URL": " http://ingestion:9090 ",
    }

    result = _resolve_bootstrap(source)

    assert result.instance_id == "ingestion-02"
    assert result.base_url == "http://ingestion:9090"
    assert result.service_name == "ingestion"


@pytest.mark.parametrize(
    "name", ["SERVICE_NAME", "INSTANCE_ID", "BASE_URL", "SERVICE_CATALOG_URL"]
)
@pytest.mark.parametrize("blank", ["", " \t "])
def test_resolve_bootstrap_blank_environment_preserves_file(
    tmp_path, bootstrap_values, name, blank
):
    path = tmp_path / "bootstrap.json"
    path.write_text(json.dumps(bootstrap_values), encoding="utf-8")
    source = {"SERVICE_BOOTSTRAP_PATH": str(path), name: blank}

    assert _resolve_bootstrap(source) == _resolve_bootstrap(bootstrap_values)


@pytest.mark.parametrize(
    "name", ["SERVICE_NAME", "INSTANCE_ID", "BASE_URL", "SERVICE_CATALOG_URL"]
)
@pytest.mark.parametrize("value", [None, "", " \t "])
def test_resolve_bootstrap_rejects_missing_final_values(
    bootstrap_values, name, value
):
    if value is None:
        del bootstrap_values[name]
    else:
        bootstrap_values[name] = value

    with pytest.raises(ConfigurationError, match=name):
        _resolve_bootstrap(bootstrap_values)


@pytest.mark.parametrize(
    "name, value",
    [
        ("SERVICE_NAME", "Ingestion"),
        ("SERVICE_NAME", "service_name"),
        ("SERVICE_NAME", "service--name"),
        ("SERVICE_NAME", "-ingestion"),
        ("SERVICE_NAME", "ingestion-"),
        ("SERVICE_NAME", "a" * 64),
        ("INSTANCE_ID", "Ingestion-01"),
        ("INSTANCE_ID", "_ingestion"),
        ("INSTANCE_ID", "ingestion_"),
        ("INSTANCE_ID", "ingestion 01"),
        ("INSTANCE_ID", "ingestión"),
        ("INSTANCE_ID", "a" * 64),
        ("SERVICE_NAME", "service/name"),
        ("SERVICE_NAME", "service+name"),
        ("SERVICE_NAME", "service#name"),
        ("INSTANCE_ID", "instance/name"),
        ("INSTANCE_ID", "instance+name"),
        ("INSTANCE_ID", "instance#name"),
    ],
)
def test_resolve_bootstrap_rejects_invalid_identifiers(
    bootstrap_values, name, value
):
    bootstrap_values[name] = value

    with pytest.raises(ConfigurationError, match=name):
        _resolve_bootstrap(bootstrap_values)


@pytest.mark.parametrize("name", ["SERVICE_NAME", "INSTANCE_ID"])
@pytest.mark.parametrize("value", ["a", "a" * 63])
def test_resolve_bootstrap_accepts_identifier_length_limits(
    bootstrap_values, name, value
):
    bootstrap_values[name] = value

    result = _resolve_bootstrap(bootstrap_values)

    assert getattr(result, name.lower()) == value


def test_resolve_bootstrap_accepts_topic_safe_instance(bootstrap_values):
    bootstrap_values["INSTANCE_ID"] = "ingestion_01-a"

    assert _resolve_bootstrap(bootstrap_values).instance_id == "ingestion_01-a"


@pytest.mark.parametrize("name", ["BASE_URL", "SERVICE_CATALOG_URL"])
@pytest.mark.parametrize("value", ["not-a-url", "http://localhost:invalid"])
def test_resolve_bootstrap_validates_urls(bootstrap_values, name, value):
    bootstrap_values[name] = value

    with pytest.raises(ConfigurationError, match=name):
        _resolve_bootstrap(bootstrap_values)


def test_resolve_bootstrap_accepts_catalog_self_bootstrap(bootstrap_values):
    bootstrap_values["SERVICE_NAME"] = "service-catalog"
    bootstrap_values["BASE_URL"] = bootstrap_values["SERVICE_CATALOG_URL"]

    result = _resolve_bootstrap(bootstrap_values)

    assert result.base_url == result.service_catalog_url


def test_resolve_bootstrap_rejects_catalog_url_mismatch(bootstrap_values):
    bootstrap_values["SERVICE_NAME"] = "service-catalog"

    with pytest.raises(ConfigurationError, match="must equal BASE_URL"):
        _resolve_bootstrap(bootstrap_values)


@pytest.mark.parametrize("file_state", ["missing", "malformed", "invalid-utf8"])
def test_resolve_bootstrap_rejects_bad_file_even_with_complete_environment(
    tmp_path, bootstrap_values, file_state
):
    path = tmp_path / "bootstrap.json"
    if file_state == "malformed":
        path.write_text("{broken", encoding="utf-8")
    elif file_state == "invalid-utf8":
        path.write_bytes(b"\xff")
    bootstrap_values["SERVICE_BOOTSTRAP_PATH"] = str(path)

    with pytest.raises(ConfigurationError):
        _resolve_bootstrap(bootstrap_values)


def test_resolve_bootstrap_ignores_unrelated_keys_without_mutation(
    tmp_path, bootstrap_values
):
    path = tmp_path / "bootstrap.json"
    file_text = json.dumps(bootstrap_values)
    path.write_text(file_text, encoding="utf-8")
    source = {
        "SERVICE_BOOTSTRAP_PATH": str(path),
        "INSTANCE_ID": "ingestion-02",
        "INFLUXDB_TOKEN": "test-only-secret",
        "MQTT_BROKER_PORT": "invalid",
        "PEER_URL": "http://arbitrary-peer:8080",
    }
    original = source.copy()

    result = _resolve_bootstrap(source)

    assert result == ServiceBootstrap(
        service_name="ingestion",
        instance_id="ingestion-02",
        base_url="http://ingestion:8080",
        service_catalog_url="http://service-catalog:8080",
    )
    assert source == original
    assert path.read_text(encoding="utf-8") == file_text


@pytest.mark.parametrize(
    "service_name, secret_field",
    [
        ("ingestion", "influxdb_token"),
        ("telegram-bot", "telegram_bot_token"),
        ("agentic-ai", "llm_api_key"),
        ("service-catalog", None),
        ("device-catalog", None),
        ("device-connector", None),
        ("operations-store", None),
        ("detection", None),
        ("response-manager", None),
        ("dashboard", None),
    ],
)
def test_load_config_only_populates_service_owned_secrets(
    bootstrap_values, service_name, secret_field
):
    source = {
        **bootstrap_values,
        "SERVICE_NAME": service_name,
        "INFLUXDB_TOKEN": "influx-test-only",
        "TELEGRAM_BOT_TOKEN": "telegram-test-only",
        "LLM_API_KEY": "llm-test-only",
        "DOCKER_INFLUXDB_INIT_ADMIN_TOKEN": "admin-test-only",
    }
    if service_name == "service-catalog":
        source["BASE_URL"] = source["SERVICE_CATALOG_URL"]
    original = source.copy()

    config = load_config(source)

    for field_name in ["influxdb_token", "telegram_bot_token", "llm_api_key"]:
        expected = source[field_name.upper()] if field_name == secret_field else None
        assert getattr(config.secrets, field_name) == expected
    for secret_name in [
        "INFLUXDB_TOKEN", "TELEGRAM_BOT_TOKEN", "LLM_API_KEY",
        "DOCKER_INFLUXDB_INIT_ADMIN_TOKEN",
    ]:
        assert source[secret_name] not in repr(config)
        assert source[secret_name] not in repr(config.secrets)
    assert source == original


@pytest.mark.parametrize(
    "service_name, secret_name",
    [("ingestion", "INFLUXDB_TOKEN"), ("telegram-bot", "TELEGRAM_BOT_TOKEN")],
)
@pytest.mark.parametrize("value", [None, "", " \t "])
def test_load_config_requires_ingestion_and_telegram_secrets(
    bootstrap_values, service_name, secret_name, value
):
    bootstrap_values["SERVICE_NAME"] = service_name
    if value is not None:
        bootstrap_values[secret_name] = value

    with pytest.raises(ConfigurationError, match=secret_name):
        load_config(bootstrap_values)


@pytest.mark.parametrize("value", [None, "", " \t "])
def test_load_config_allows_keyless_ai_provider(bootstrap_values, value):
    bootstrap_values["SERVICE_NAME"] = "agentic-ai"
    if value is not None:
        bootstrap_values["LLM_API_KEY"] = value

    assert load_config(bootstrap_values).secrets.llm_api_key is None


@pytest.mark.parametrize(
    "service_name, secret_name",
    [
        ("ingestion", "INFLUXDB_TOKEN"),
        ("telegram-bot", "TELEGRAM_BOT_TOKEN"),
        ("agentic-ai", "LLM_API_KEY"),
    ],
)
def test_load_config_rejects_padded_owned_secret_without_exposing_it(
    bootstrap_values, service_name, secret_name
):
    bootstrap_values["SERVICE_NAME"] = service_name
    bootstrap_values[secret_name] = " padded-test-secret "

    with pytest.raises(ConfigurationError, match=secret_name) as error:
        load_config(bootstrap_values)

    assert "padded-test-secret" not in str(error.value)
    assert "padded-test-secret" not in repr(error.value)


def test_load_config_ignores_malformed_unowned_secrets(bootstrap_values):
    source = {
        **bootstrap_values,
        "SERVICE_NAME": "dashboard",
        "INFLUXDB_TOKEN": " padded-influx-secret ",
        "TELEGRAM_BOT_TOKEN": " padded-telegram-secret ",
        "LLM_API_KEY": " padded-llm-secret ",
    }

    config = load_config(source)

    assert config.secrets.influxdb_token is None
    assert config.secrets.telegram_bot_token is None
    assert config.secrets.llm_api_key is None


def test_load_config_does_not_reuse_influx_admin_token(bootstrap_values):
    bootstrap_values["DOCKER_INFLUXDB_INIT_ADMIN_TOKEN"] = "admin-test-only"

    with pytest.raises(ConfigurationError, match="INFLUXDB_TOKEN"):
        load_config(bootstrap_values)


def test_load_config_reads_process_environment_at_call_time(
    monkeypatch, bootstrap_values
):
    for name, value in bootstrap_values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("SERVICE_BOOTSTRAP_PATH", raising=False)
    monkeypatch.setenv("INFLUXDB_TOKEN", "environment-test-only")

    config = load_config()

    assert config.bootstrap.service_name == "ingestion"
    assert config.secrets.influxdb_token == "environment-test-only"


def test_load_config_explicit_source_does_not_fall_back_to_environment(
    monkeypatch, bootstrap_values
):
    for name, value in bootstrap_values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("INFLUXDB_TOKEN", "environment-test-only")

    with pytest.raises(ConfigurationError, match="SERVICE_NAME"):
        load_config({})
    with pytest.raises(ConfigurationError, match="INFLUXDB_TOKEN"):
        load_config(bootstrap_values)


def test_load_config_creates_new_uuid4_per_startup_config(bootstrap_values):
    source = {
        **bootstrap_values,
        "INFLUXDB_TOKEN": "test-only-token",
        "SERVICE_ID": "svc_do-not-use-this",
    }

    first = load_config(source)
    second = load_config(source)

    assert first.bootstrap == second.bootstrap
    assert first.service_id != second.service_id
    for config in [first, second]:
        assert config.service_id.startswith("svc_")
        identifier = UUID(config.service_id[4:])
        assert identifier.version == 4
        assert config.service_id == f"svc_{identifier}"


@pytest.mark.parametrize("invalid_part", ["bootstrap", "secret"])
def test_load_config_validates_before_generating_identity(
    monkeypatch, bootstrap_values, invalid_part
):
    def unexpected_uuid():
        pytest.fail("Invalid configuration must fail before generating an ID.")

    monkeypatch.setattr("common.config.loader.uuid4", unexpected_uuid)
    if invalid_part == "bootstrap":
        bootstrap_values["SERVICE_NAME"] = "Invalid"
        bootstrap_values["INFLUXDB_TOKEN"] = "test-only-token"

    with pytest.raises(ConfigurationError):
        load_config(bootstrap_values)
