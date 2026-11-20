import json

import pytest

from sensai.features.persona.loader import (
    PersonaError,
    build_identity,
    list_personas,
    load_persona,
)


def _write(tmp_path, name, data):
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_persona_valid(tmp_path):
    _write(tmp_path, "mentor", {"name": "CodeMentor", "role": "a mentor"})
    persona = load_persona("mentor", str(tmp_path))
    assert persona["name"] == "CodeMentor"


def test_load_persona_missing_file(tmp_path):
    with pytest.raises(PersonaError, match="Could not read"):
        load_persona("nope", str(tmp_path))


def test_load_persona_invalid_json(tmp_path):
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(PersonaError, match="not valid JSON"):
        load_persona("bad", str(tmp_path))


def test_load_persona_missing_required_field(tmp_path):
    _write(tmp_path, "incomplete", {"name": "NoRole"})
    with pytest.raises(PersonaError, match="missing the required field 'role'"):
        load_persona("incomplete", str(tmp_path))


def test_list_personas(tmp_path):
    _write(tmp_path, "b_persona", {"name": "B", "role": "r"})
    _write(tmp_path, "a_persona", {"name": "A", "role": "r"})
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")

    assert list_personas(str(tmp_path)) == ["a_persona", "b_persona"]


def test_list_personas_missing_dir():
    assert list_personas("does_not_exist_dir") == []


def test_build_identity_full():
    persona = {
        "name": "CodeMentor",
        "role": "a patient mentor",
        "tone": "encouraging",
        "scope": "Focus on code.",
    }
    identity = build_identity(persona)
    assert identity == (
        "You are CodeMentor, a patient mentor. Your tone is encouraging. Focus on code."
    )


def test_build_identity_minimal():
    identity = build_identity({"name": "Bot", "role": "an assistant"})
    assert identity == "You are Bot, an assistant."
