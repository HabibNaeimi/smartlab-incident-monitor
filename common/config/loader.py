import json
import os
import re
from pathlib import Path
from uuid import uuid4
from collections.abc import Mapping
from .env import ConfigurationError
from .settings import AppConfig, ServiceBootstrap, ServiceSecrets
from .env import (
    get_optional_str,
    get_required_str,
    get_secret,
    get_url,
)

_BOOTSTRAP_KEYS = frozenset(
    {
        "SERVICE_NAME",
        "INSTANCE_ID",
        "BASE_URL",
        "SERVICE_CATALOG_URL",
    }
)

def _read_bootstrap_file(path: Path) -> dict[str, str]:
    """
    Read a JSON object containing only the four string bootstrap fields.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            text = f.read()
    except(OSError, UnicodeDecodeError):
        raise ConfigurationError(f"Could not read bootstrap file '{path}' as UTF-8 text.") from None
        
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        raise ConfigurationError("Bootstrap file must contain valid JSON.") from None
    
    if not isinstance(parsed, dict):
        raise ConfigurationError("Bootstrap file must contain a JSON object.")
    
    unknown_keys = set(parsed) - _BOOTSTRAP_KEYS
    if unknown_keys:
        raise ConfigurationError(f"Unknown bootstrap keys: {', '.join(sorted(unknown_keys))}.")
    
    for key, value in parsed.items():
        if not isinstance(value, str):
            raise ConfigurationError(f"Bootstrap value for '{key}' must be a string.")

    return parsed


def _resolve_bootstrap(source: Mapping[str, str]) -> ServiceBootstrap:
    """Resolve the optional file, apply environment overrides, then validate."""
    path = get_optional_str(source, "SERVICE_BOOTSTRAP_PATH")
    values = _read_bootstrap_file(Path(path)) if path is not None else {}

    for name in _BOOTSTRAP_KEYS:
        value = get_optional_str(source, name)
        if value is not None:
            values[name] = value

    service_name = get_required_str(values, "SERVICE_NAME")
    instance_id = get_required_str(values, "INSTANCE_ID")
    if len(service_name) > 63 or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", service_name
    ):
        raise ConfigurationError(
            "SERVICE_NAME must be lowercase kebab case, 1-63 characters."
        )
    if len(instance_id) > 63 or not re.fullmatch(
        r"[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?", instance_id
    ):
        raise ConfigurationError(
            "INSTANCE_ID must be 1-63 lowercase letters, digits, '-' or '_', "
            "starting and ending with a letter or digit."
        )

    base_url = get_url(values, "BASE_URL")
    catalog_url = get_url(values, "SERVICE_CATALOG_URL")
    if service_name == "service-catalog" and catalog_url != base_url:
        raise ConfigurationError(
            "SERVICE_CATALOG_URL must equal BASE_URL for service-catalog."
        )

    return ServiceBootstrap(
        service_name=service_name,
        instance_id=instance_id,
        base_url=base_url,
        service_catalog_url=catalog_url,
    )


def load_config(source: Mapping[str, str] | None = None) -> AppConfig:
    """Load once at service startup; reuse the result for retries and heartbeats.

    With no explicit mapping, read the process environment at call time.
    Each successful call creates a new service ID; imports do not create one.
    """
    values = os.environ if source is None else source
    bootstrap = _resolve_bootstrap(values)

    secrets = ServiceSecrets()
    if bootstrap.service_name == "ingestion":
        secrets = ServiceSecrets(
            influxdb_token=get_secret(values, "INFLUXDB_TOKEN", required=True)
        )
    elif bootstrap.service_name == "telegram-bot":
        secrets = ServiceSecrets(
            telegram_bot_token=get_secret(values, "TELEGRAM_BOT_TOKEN", required=True)
        )
    elif bootstrap.service_name == "agentic-ai":
        # A local/fake provider may need no key. The provider checks its needs.
        secrets = ServiceSecrets(llm_api_key=get_secret(values, "LLM_API_KEY"))

    return AppConfig(
        bootstrap=bootstrap,
        service_id=f"svc_{uuid4()}",
        secrets=secrets,
    )
