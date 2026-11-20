import json
import math
import os
from dataclasses import dataclass

DEFAULT_CONFIG_PATH = "config.json"
DEFAULT_MODEL = "llama3.2"
DEFAULT_OLLAMA_URL = "http://localhost:11434"


class ConfigError(Exception):
    pass


@dataclass
class Config:
    model: str
    ollama_url: str
    persona: str | None = None
    temperature: float | None = None
    num_ctx: int | None = None

    @property
    def options(self) -> dict:
        """Ollama generation options; unset values are left to Ollama's defaults."""
        options = {}
        if self.temperature is not None:
            options["temperature"] = self.temperature
        if self.num_ctx is not None:
            options["num_ctx"] = self.num_ctx
        return options


def _read_config_file(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Config file '{path}' is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Config file '{path}' must contain a JSON object.")
    return data


def _validate_temperature(value) -> float | None:
    if value is None:
        return None
    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if not is_number or not math.isfinite(value) or value < 0:
        raise ConfigError(f"'temperature' must be a number >= 0, got {value!r}.")
    return value


def _validate_num_ctx(value) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfigError(f"'num_ctx' must be a positive integer, got {value!r}.")
    return value


def load_config(
    config_path: str | None,
    model_override: str | None,
    temperature_override: float | None = None,
    num_ctx_override: int | None = None,
) -> Config:
    data = _read_config_file(config_path or DEFAULT_CONFIG_PATH)

    model = model_override or data.get("model", DEFAULT_MODEL)
    ollama_url = data.get("ollama_url", DEFAULT_OLLAMA_URL)
    persona = data.get("persona") or None
    # `is not None`, not `or`: a temperature of 0 is a valid override.
    temperature = temperature_override if temperature_override is not None else data.get("temperature")
    num_ctx = num_ctx_override if num_ctx_override is not None else data.get("num_ctx")
    return Config(
        model=model,
        ollama_url=ollama_url,
        persona=persona,
        temperature=_validate_temperature(temperature),
        num_ctx=_validate_num_ctx(num_ctx),
    )
