import json

import pytest

from sensai.features.structured_output.schema import (
    SchemaError,
    describe_schema,
    load_schema,
    validate_output,
)

PERSON_SCHEMA = {
    "title": "Person",
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
    },
    "required": ["name", "age"],
    "additionalProperties": False,
}


def test_load_schema_reads_valid_file(tmp_path):
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(PERSON_SCHEMA), encoding="utf-8")

    assert load_schema(str(path)) == PERSON_SCHEMA


def test_load_schema_missing_file():
    with pytest.raises(SchemaError, match="Could not read"):
        load_schema("does_not_exist.json")


def test_load_schema_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(SchemaError, match="not valid JSON"):
        load_schema(str(path))


def test_load_schema_invalid_schema(tmp_path):
    path = tmp_path / "bad_schema.json"
    path.write_text(json.dumps({"type": "not_a_real_type"}), encoding="utf-8")

    with pytest.raises(SchemaError, match="not a valid JSON Schema"):
        load_schema(str(path))


def test_validate_output_accepts_conforming_json():
    output = json.dumps({"name": "Younes", "age": 22})
    assert validate_output(output, PERSON_SCHEMA) == {"name": "Younes", "age": 22}


def test_validate_output_rejects_non_json():
    with pytest.raises(SchemaError, match="not valid JSON"):
        validate_output("I am not JSON", PERSON_SCHEMA)


def test_validate_output_rejects_schema_mismatch():
    output = json.dumps({"name": "Younes"})  # missing required 'age'
    with pytest.raises(SchemaError, match="does not match schema"):
        validate_output(output, PERSON_SCHEMA)


def test_validate_output_rejects_wrong_type():
    output = json.dumps({"name": "Younes", "age": "twenty"})  # age must be integer
    with pytest.raises(SchemaError, match="does not match schema"):
        validate_output(output, PERSON_SCHEMA)


def test_describe_schema_lists_fields():
    description = describe_schema(PERSON_SCHEMA)
    assert "Person" in description
    assert "name" in description
    assert "age" in description


def test_describe_schema_without_properties():
    description = describe_schema({"type": "object"})
    assert "JSON" in description
