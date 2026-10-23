import json
from pathlib import Path
from .env import ConfigurationError

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
    Function to pars bootstrap file, handling malformed JSON and filesystem errors
        Validating the top-level structure, rejecting unsupported keys, and ensuring str output. 
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
