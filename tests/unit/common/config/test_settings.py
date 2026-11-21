

from dataclasses import FrozenInstanceError
import pytest
from common.config.settings import AppConfig, ServiceBootstrap, ServiceSecrets


# Construction test
def test_configuration_objects_can_be_constructed_with_valid_values():
    bootstrap = ServiceBootstrap(
        service_name="ingestion", 
        instance_id="ingestion-1",
        base_url="http://ingestion:8080",
        service_catalog_url="http://service-catalog:8080",
                            )
    secrets = ServiceSecrets(
        influxdb_token="influx-secret-for-test-only",
        telegram_bot_token="telegram-secret-for-test-only",
        llm_api_key="llm-secret-for-test-only",
    )
    app_config = AppConfig(
        bootstrap=bootstrap,
        service_id="svc_123e4567-e89b-42d3-a456-426614174000",
        secrets=secrets,
    )

    assert app_config.bootstrap == bootstrap
    assert app_config.secrets == secrets
    assert app_config.service_id == "svc_123e4567-e89b-42d3-a456-426614174000"

# Frozen-object test
def test_configuration_objects_are_frozen():
    bootstrap = ServiceBootstrap(
        service_name="ingestion", 
        instance_id="ingestion-1",
        base_url="http://ingestion:8080",
        service_catalog_url="http://service-catalog:8080",
                            )
    secrets = ServiceSecrets(
        influxdb_token="influx-secret-for-test-only",
        telegram_bot_token="telegram-secret-for-test-only",
        llm_api_key="llm-secret-for-test-only",
    )
    app_config = AppConfig(
        bootstrap=bootstrap,
        service_id="svc_123e4567-e89b-42d3-a456-426614174000",
        secrets=secrets,
    )

    with pytest.raises(FrozenInstanceError):
        bootstrap.service_name = "changed"

    with pytest.raises(FrozenInstanceError):
        secrets.influxdb_token = "changing_token"

    with pytest.raises(FrozenInstanceError):
        app_config.service_id = "changing_id"

# Secret-representation test
def test_secret_values_are_hidden_from_repr():
    bootstrap = ServiceBootstrap(
        service_name="ingestion", 
        instance_id="ingestion-1",
        base_url="http://ingestion:8080",
        service_catalog_url="http://service-catalog:8080",
                            )
    secrets = ServiceSecrets(
        influxdb_token="influx-secret-for-test-only",
        telegram_bot_token="telegram-secret-for-test-only",
        llm_api_key="llm-secret-for-test-only",
    )
    app_config = AppConfig(
        bootstrap=bootstrap,
        service_id="svc_123e4567-e89b-42d3-a456-426614174000",
        secrets=secrets,
    )
    supplied_secret_values = (
        secrets.influxdb_token,
        secrets.telegram_bot_token,
        secrets.llm_api_key,
    )
    for secret_value in supplied_secret_values:
        assert secret_value not in repr(secrets)
        assert secret_value not in repr(app_config)