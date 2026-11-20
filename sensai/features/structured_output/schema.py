import json

import jsonschema


class SchemaError(Exception):
    pass


def load_schema(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            schema = json.load(f)
    except OSError as exc:
        raise SchemaError(f"Could not read schema file '{path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SchemaError(f"Schema file '{path}' is not valid JSON: {exc}") from exc

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        raise SchemaError(f"Schema file '{path}' is not a valid JSON Schema: {exc.message}") from exc

    return schema


def validate_output(output: str, schema: dict) -> dict:
    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"Model output is not valid JSON: {exc}") from exc

    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        raise SchemaError(f"Output does not match schema: {exc.message}") from exc

    return data


def describe_schema(schema: dict) -> str:
    title = schema.get("title", "the requested schema")
    properties = schema.get("properties")
    if not properties:
        return f"Respond only with JSON matching {title}."
    fields = ", ".join(properties.keys())
    return f"Respond only with JSON matching {title}, containing these fields: {fields}."
