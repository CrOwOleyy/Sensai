import json

import pytest

from sensai.core.config import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, ConfigError, load_config


def test_defaults_when_no_config_file(tmp_path):
    config = load_config(str(tmp_path / "missing.json"), None)
    assert config.model == DEFAULT_MODEL
    assert config.ollama_url == DEFAULT_OLLAMA_URL
    assert config.persona is None


def test_cli_override_wins_over_config_file(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"model": "from-file"}), encoding="utf-8")

    config = load_config(str(config_path), "from-cli")
    assert config.model == "from-cli"


def test_config_file_used_when_no_override(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"model": "from-file", "persona": "mentor"}), encoding="utf-8")

    config = load_config(str(config_path), None)
    assert config.model == "from-file"
    assert config.persona == "mentor"


def _write_config(tmp_path, data):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_generation_options_are_empty_when_unset(tmp_path):
    config = load_config(str(tmp_path / "missing.json"), None)
    assert config.options == {}


def test_generation_options_read_from_config_file(tmp_path):
    config = load_config(_write_config(tmp_path, {"temperature": 0.2, "num_ctx": 8192}), None)
    assert config.options == {"temperature": 0.2, "num_ctx": 8192}


def test_cli_overrides_win_over_config_file(tmp_path):
    path = _write_config(tmp_path, {"temperature": 0.2, "num_ctx": 8192})
    config = load_config(path, None, temperature_override=0.9, num_ctx_override=2048)
    assert config.options == {"temperature": 0.9, "num_ctx": 2048}


def test_zero_temperature_is_kept(tmp_path):
    path = _write_config(tmp_path, {"temperature": 0.7})
    assert load_config(path, None, temperature_override=0.0).options == {"temperature": 0.0}
    assert load_config(_write_config(tmp_path, {"temperature": 0}), None).options == {"temperature": 0}


@pytest.mark.parametrize(
    "data",
    [
        {"temperature": -1},
        {"temperature": "hot"},
        {"temperature": True},
        {"temperature": float("nan")},
        {"num_ctx": 0},
        {"num_ctx": -4096},
        {"num_ctx": 4096.5},
        {"num_ctx": "big"},
        {"num_ctx": True},
    ],
)
def test_invalid_generation_options_are_rejected(tmp_path, data):
    with pytest.raises(ConfigError):
        load_config(_write_config(tmp_path, data), None)


@pytest.mark.parametrize("content", ["{bad json", "[1, 2]"])
def test_malformed_config_file_is_rejected(tmp_path, content):
    path = tmp_path / "config.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(str(path), None)
