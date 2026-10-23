

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)      
class ServiceBootstrap:
    service_name: str
    instance_id: str
    base_url: str
    service_catalog_url: str

@dataclass(frozen=True, slots=True)
class ServiceSecrets:
    influxdb_token: str | None = field(default=None, repr=False)       # All secret fields are str | None, 
    telegram_bot_token: str | None = field(default=None, repr=False)   #   default to None, and must be 
    llm_api_key: str | None = field(default=None, repr=False)          #   hidden from representations.

@dataclass(frozen=True, slots=True)
class AppConfig:
    bootstrap: ServiceBootstrap
    service_id: str
    secrets: ServiceSecrets = field(repr=False)
