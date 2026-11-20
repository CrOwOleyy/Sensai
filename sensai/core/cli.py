import argparse
import json
from pathlib import Path
import sys

from sensai.core import db
from sensai.core.config import ConfigError, load_config
from sensai.core.ollama_client import OllamaConnectionError, OllamaModelError, chat, stream_chat
from sensai.core.prompt import build_system_prompt
from sensai.features.content_guardrails.guardrails import (
    inspect_user_input,
    sanitize_output,
    stream_sanitized_output,
)
from sensai.features.persona.loader import (
    PersonaError,
    build_identity,
    list_personas,
    load_persona,
)
from sensai.features.session_persistence.export import render_json, render_markdown
from sensai.features.session_persistence import store as session_store
from sensai.features.structured_memory import store as memory_store
from sensai.features.structured_memory.resolver import resolve_tool_calls
from sensai.features.structured_memory.tools import INSTRUCTIONS as MEMORY_INSTRUCTIONS
from sensai.features.structured_output.schema import (
    SchemaError,
    describe_schema,
    load_schema,
    validate_output,
)

EXIT_COMMANDS = {"exit", "quit"}
EXPORT_FORMATS = {"json", "markdown"}


def _apply_identity(
    messages: list[dict],
    conn,
    identity: str | None,
    feature_instructions: list[str] | None = None,
) -> list[dict]:
    instructions = (
        feature_instructions if feature_instructions is not None else [MEMORY_INSTRUCTIONS]
    )
    system_prompt = build_system_prompt(
        session_store.get_profile(conn), instructions, identity=identity
    )
    body = [m for m in messages if m["role"] != "system"]
    return [{"role": "system", "content": system_prompt}, *body]


def _export_session(session_id: int, messages: list[dict], export_format: str, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if export_format == "json":
        content = render_json(session_id, messages)
    else:
        content = render_markdown(session_id, messages)
    path.write_text(content, encoding="utf-8")
    print(f"Exported session #{session_id} to {path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="sensai", description="Sensai CLI chatbot")
    parser.add_argument("--model", help="Ollama model name (overrides config file)")
    parser.add_argument(
        "--temperature", type=float, default=None, help="Sampling temperature (overrides config file)"
    )
    parser.add_argument(
        "--num-ctx", type=int, default=None, help="Context window size in tokens (overrides config file)"
    )
    parser.add_argument("--config", help="Path to a JSON config file", default=None)
    parser.add_argument("--db", help="Path to the SQLite database", default=db.DEFAULT_DB_PATH)
    parser.add_argument(
        "--resume", action="store_true", help="Continue the most recent session instead of starting a new one"
    )
    parser.add_argument(
        "--set-profile",
        action="append",
        metavar="KEY=VALUE",
        default=[],
        help="Set a persistent profile entry (repeatable), e.g. --set-profile name=Ryad",
    )
    parser.add_argument(
        "--persona",
        metavar="NAME",
        default=None,
        help="Start with a persona from the personas/ directory (switch at runtime with /persona NAME)",
    )
    parser.add_argument(
        "--schema",
        metavar="PATH",
        default=None,
        help="Path to a JSON Schema file; responses are constrained to valid JSON matching it",
    )
    parser.add_argument(
        "--export",
        nargs=2,
        metavar=("FORMAT", "PATH"),
        help="Export the latest stored session to JSON or Markdown and exit",
    )
    return parser.parse_args(argv)


def run() -> None:
    args = parse_args()
    try:
        config = load_config(args.config, args.model, args.temperature, args.num_ctx)
    except ConfigError as exc:
        print(f"[error] {exc}")
        return
    conn = db.connect(
        args.db,
        schemas=(session_store.SCHEMA, memory_store.SCHEMA),
    )

    for entry in args.set_profile:
        key, _, value = entry.partition("=")
        session_store.set_profile_value(conn, key.strip(), value.strip())

    if args.export:
        export_format, output_path = args.export
        if export_format not in EXPORT_FORMATS:
            print("Usage: --export json|markdown PATH")
            return
        latest_session_id = session_store.get_latest_session_id(conn)
        if latest_session_id is None:
            print("[error] No session found to export.")
            return
        _export_session(
            latest_session_id,
            session_store.load_messages(conn, latest_session_id),
            export_format,
            output_path,
        )
        return

    identity = None
    persona_name = args.persona or config.persona
    persona_label = "default"
    if persona_name:
        try:
            persona = load_persona(persona_name)
        except PersonaError as exc:
            print(f"[error] {exc}")
            return
        identity = build_identity(persona)
        persona_label = persona["name"]

    structured_schema = None
    if args.schema:
        try:
            structured_schema = load_schema(args.schema)
        except SchemaError as exc:
            print(f"[error] {exc}")
            return
        feature_instructions = [describe_schema(structured_schema)]
    else:
        feature_instructions = [MEMORY_INSTRUCTIONS]

    if args.resume and (session_id := session_store.get_latest_session_id(conn)) is not None:
        messages = session_store.load_messages(conn, session_id)
        print(f"Resuming session #{session_id} ({len(messages)} prior messages)")
    else:
        session_id = session_store.create_session(conn)
        messages = []

    messages = _apply_identity(messages, conn, identity, feature_instructions)

    mode = "JSON schema" if structured_schema else "chat"
    print(
        f"Sensai chatbot — model: {config.model}, persona: {persona_label}, mode: {mode} (type 'exit' or '/help')"
    )

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            print("Please enter a non-empty message.")
            continue

        guardrail = inspect_user_input(user_input)
        if not guardrail.allowed:
            print(f"[guardrail] {guardrail.message}")
            continue

        if user_input in {"/help", "help"}:
            print("Available commands:")
            print("  /personas                      - List available personas (Hogwarts professors)")
            print("  /persona <name>                - Switch persona (e.g. /persona snape)")
            print("  /export <json|markdown> <path> - Export conversation history")
            print("  exit | quit                    - Leave the chat")
            continue

        if user_input == "/personas":
            available = list_personas()
            print("Available personas:", ", ".join(available) if available else "(none)")
            continue

        if user_input.startswith("/export"):
            parts = user_input.split(maxsplit=2)
            if len(parts) != 3:
                print("Usage: /export json|markdown PATH")
                continue
            _, export_format, output_path = parts
            if export_format not in EXPORT_FORMATS:
                print("Usage: /export json|markdown PATH")
                continue
            try:
                _export_session(session_id, messages, export_format, output_path)
            except OSError as exc:
                print(f"[error] Could not export session: {exc}")
            continue

        if user_input.startswith("/persona "):
            name = user_input[len("/persona "):].strip()
            try:
                persona = load_persona(name)
            except PersonaError as exc:
                print(f"[error] {exc}")
                continue
            identity = build_identity(persona)
            messages = _apply_identity(messages, conn, identity, feature_instructions)
            print(f"Switched to persona: {persona['name']} (conversation history kept)")
            continue

        if user_input.lower() in EXIT_COMMANDS:
            print("Goodbye.")
            break

        turn_start = len(messages)
        messages.append({"role": "user", "content": user_input})
        session_store.save_message(conn, session_id, "user", user_input)

        if structured_schema is not None:
            try:
                message = chat(
                    config.ollama_url,
                    config.model,
                    messages,
                    format_=structured_schema,
                    options=config.options,
                )
            except (OllamaConnectionError, OllamaModelError) as exc:
                print(f"[error] {exc}")
                del messages[turn_start:]
                continue

            raw = message.get("content", "")
            try:
                data = validate_output(raw, structured_schema)
            except SchemaError as exc:
                print(f"[schema error] {exc}")
                print(f"Raw output: {raw}")
                del messages[turn_start:]
                continue

            reply = sanitize_output(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"Assistant (JSON):\n{reply}")
            messages.append({"role": "assistant", "content": reply})
            session_store.save_message(conn, session_id, "assistant", reply)
            continue

        try:
            messages = resolve_tool_calls(
                conn, config.ollama_url, config.model, messages, options=config.options
            )
        except (OllamaConnectionError, OllamaModelError) as exc:
            print(f"[error] {exc}")
            del messages[turn_start:]
            continue

        print("Assistant: ", end="", flush=True)
        reply_chunks: list[str] = []
        try:
            for sanitized_chunk in stream_sanitized_output(
                stream_chat(config.ollama_url, config.model, messages, options=config.options)
            ):
                reply_chunks.append(sanitized_chunk)
                print(sanitized_chunk, end="", flush=True)
        except (OllamaConnectionError, OllamaModelError) as exc:
            print(f"\n[error] {exc}")
            del messages[turn_start:]
            continue
        print()

        reply = "".join(reply_chunks)

        messages.append({"role": "assistant", "content": reply})
        session_store.save_message(conn, session_id, "assistant", reply)


if __name__ == "__main__":
    sys.exit(run())
