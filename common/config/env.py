from collections.abc import Mapping
from urllib.parse import urlsplit
import math


class ConfigurationError(ValueError):
    pass
    

def get_required_str(
    source: Mapping[str, str],
    name: str,
) -> str:
    
    value = source.get(name)
    if value is None or not value.strip():      # Detect missing or blank values and also "" and " ".
        raise ConfigurationError(f"Required environment variable '{name}' is missing or empty. Expectation: str")
    else:
        return value.strip()


def get_optional_str(
    source: Mapping[str, str],
    name: str,
    default: str | None = None,
) -> str | None:
    
    value = source.get(name)
    if value is None or not value.strip():
        return default
    else:
        return value.strip()
    

def get_int(
    source: Mapping[str, str],
    name: str,
    *,
    default: int | None = None,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    
    value = source.get(name)
    if value is None or not value.strip():
        if default==None:
            raise ConfigurationError(
                f"Required environment variable '{name}' is missing or empty. Expectation: int"
            )
        else:
            return default
    
    try:
        parsed = int(value.strip())
    except ValueError:
        raise ConfigurationError(
            f"Required environment variable '{name}' should be int and not None."
        ) from None
    
    if minimum is not None and parsed < minimum:
        raise ConfigurationError(
            f"Required environment variable '{name}' must be an int"

            f"greater than or equal to {minimum}."
        )
    if maximum is not None and parsed > maximum:
        raise ConfigurationError(
            f"Required environment variable '{name}' must be an int"

            f"less than or equal to {maximum}."
        )
    return parsed


def get_float(
    source: Mapping[str, str],
    name: str,
    *,
    default: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    
    value = source.get(name)
    if value is None or not value.strip():
        if default==None:
            raise ConfigurationError(
                f"Required environment variable '{name}' is missing or empty. Expectation: float"
            )
        else:
            return default
    try:
        parsed = float(value.strip())
    except ValueError:
        raise ConfigurationError(
            f"Environment variable '{name}' must be a float in the inclusive range [{minimum}, {maximum}]."
        ) from None
    
    if not math.isfinite(parsed):
        raise ConfigurationError(
            f"Required environment variable '{name}' must be a finite float."
        )
    if minimum is not None and parsed < minimum:
        raise ConfigurationError(
            f"Required environment variable '{name}' smust be a float."

            f"greater than or equal to {minimum}."
        )
    if maximum is not None and parsed > maximum:
        raise ConfigurationError(
            f"Required environment variable '{name}' must be a float"

            f"less than or equal to {maximum}."
        )
    return parsed
    

def get_bool(
    source: Mapping[str, str],
    name: str,
    *,
    default: bool | None = None,
) -> bool:
    
    value = source.get(name)
    if value is None or not value.strip():
        if default==None:
            raise ConfigurationError(
                f"Required environment variable '{name}' is missing or empty. Expectation: bool"
            )
        else:
            return default
    
    normalized = value.strip().lower()
    
    if normalized in {"1", "true", "yes", "on"}:
        return True
    
    if normalized in {"0", "false", "no", "off"}:
        return False
    
    else: 
        raise ConfigurationError(
            f"Required environment variable '{name}' must be bool. Accepted tokens: 1, true, yes, on, 0, false, no, off"
        )
    

def get_url(
    source: Mapping[str, str],
    name: str,
) -> str:
    
    value = get_required_str(source, name)
    if any(character.isspace() for character in value):
        raise ConfigurationError(
            f"Required environment variable '{name}' must not contain whitespace."
        )
    
    try:
        parsed_url = urlsplit(url=value)
        hostname = parsed_url.hostname
        _ = parsed_url.port
    except ValueError:
        raise ConfigurationError(
            f"Environment variable '{name}' must contain a valid URL and port."
        ) from None
    
    if parsed_url.scheme not in {"http", "https"}:
        raise ConfigurationError(
            f"The scheme of environment variable '{name}' must be http or https."
        )
    if not hostname:
        raise ConfigurationError(
            f"Environment variable '{name}' must contain a hostname."
        )
    
    if parsed_url.username is not None or parsed_url.password is not None:
        raise ConfigurationError(
            f"Environment variable '{name}' must not contain embedded credentials."
        )
    
    if parsed_url.query or parsed_url.fragment:
        raise ConfigurationError(
            f"Environment variable '{name}' must not contain a query string or fragment."
        )
    
    if value.endswith("/"):
        raise ConfigurationError(
            f"Environment variable '{name}' must not end with '/'."
        )
    return value
    

def get_secret(
    source: Mapping[str, str],
    name: str,
    *,
    required: bool = False,
) -> str | None:
    
    value = source.get(name)
    if value is None or not value.strip():
        if required:
            raise ConfigurationError(
                f"Secret environment variable '{name}' is missing or empty. Expectation: str"
            )
        else:
            return None
        
    if value != value.strip():
        raise ConfigurationError(
            f"Secret environment variable '{name}' must not contain surrounding whitespace."
        )
    return value