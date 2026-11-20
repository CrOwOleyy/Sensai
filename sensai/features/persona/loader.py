import json
import os

DEFAULT_PERSONAS_DIR = "personas"


class PersonaError(Exception):
    pass


def _persona_path(name: str, personas_dir: str) -> str:
    return os.path.join(personas_dir, f"{name}.json")


def load_persona(name: str, personas_dir: str = DEFAULT_PERSONAS_DIR) -> dict:
    path = _persona_path(name, personas_dir)
    try:
        with open(path, encoding="utf-8") as f:
            persona = json.load(f)
    except OSError as exc:
        raise PersonaError(f"Could not read persona '{name}' at '{path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PersonaError(f"Persona file '{path}' is not valid JSON: {exc}") from exc

    for field in ("name", "role"):
        if not persona.get(field):
            raise PersonaError(f"Persona '{name}' is missing the required field '{field}'.")

    return persona


def list_personas(personas_dir: str = DEFAULT_PERSONAS_DIR) -> list[str]:
    if not os.path.isdir(personas_dir):
        return []
    names = [
        filename[:-5]
        for filename in os.listdir(personas_dir)
        if filename.endswith(".json")
    ]
    return sorted(names)


def build_identity(persona: dict) -> str:
    parts = [f"You are {persona['name']}, {persona['role']}."]
    if tone := persona.get("tone"):
        parts.append(f"Your tone is {tone}.")
    if scope := persona.get("scope"):
        parts.append(scope)
    return " ".join(parts)
