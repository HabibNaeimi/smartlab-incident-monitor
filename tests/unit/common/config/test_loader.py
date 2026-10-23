from common.config.loader import _read_bootstrap_file
from common.config.env import ConfigurationError
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

