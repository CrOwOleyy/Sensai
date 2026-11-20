import argparse
import json
import os
from collections.abc import Iterator

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from sensai.core import db
from sensai.core.config import Config, ConfigError, load_config
from sensai.core.ollama_client import (
    OllamaConnectionError,
    OllamaModelError,
    list_models,
    stream_chat,
)
from sensai.core.prompt import build_system_prompt
from sensai.features.content_guardrails.guardrails import inspect_user_input, stream_sanitized_output
from sensai.features.persona.loader import (
    DEFAULT_PERSONAS_DIR,
    PersonaError,
    build_identity,
    list_personas,
    load_persona,
)
from sensai.features.session_persistence import store as session_store
from sensai.features.session_persistence.export import render_json, render_markdown
from sensai.features.structured_memory import store as memory_store
from sensai.features.structured_memory.resolver import resolve_tool_calls
from sensai.features.structured_memory.tools import INSTRUCTIONS as MEMORY_INSTRUCTIONS

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class ChatRequest(BaseModel):
    session_id: int
    message: str
    persona: str | None = None
    model: str | None = None


class ProfileUpdate(BaseModel):
    values: dict[str, str]


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def create_app(
    config: Config, db_path: str = db.DEFAULT_DB_PATH, personas_dir: str = DEFAULT_PERSONAS_DIR
) -> FastAPI:
    app = FastAPI(title="Sensai")

    def connect():
        return db.connect(db_path, schemas=(session_store.SCHEMA, memory_store.SCHEMA))

    def identity_for(persona_name: str | None) -> str | None:
        if not persona_name:
            persona_name = config.persona
        if not persona_name:
            return None
        try:
            return build_identity(load_persona(persona_name, personas_dir))
        except PersonaError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/")
    def index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/api/state")
    def state():
        conn = connect()
        try:
            sessions = conn.execute(
                "SELECT s.id, s.created_at, "
                "(SELECT content FROM messages m WHERE m.session_id = s.id AND m.role = 'user' "
                " ORDER BY m.id LIMIT 1) AS title "
                "FROM sessions s ORDER BY s.id DESC"
            ).fetchall()
            profile = session_store.get_profile(conn)
        finally:
            conn.close()
        try:
            models = list_models(config.ollama_url)
        except OllamaConnectionError:
            models = []
        return {
            "model": config.model,
            "models": models,
            "persona": config.persona,
            "personas": list_personas(personas_dir),
            "profile": profile,
            "sessions": [dict(row) for row in sessions],
        }

    @app.post("/api/sessions")
    def new_session():
        conn = connect()
        try:
            return {"id": session_store.create_session(conn)}
        finally:
            conn.close()

    @app.get("/api/sessions/{session_id}")
    def get_session(session_id: int):
        conn = connect()
        try:
            exists = conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail="Session not found")
            return {"messages": session_store.load_messages(conn, session_id)}
        finally:
            conn.close()

    @app.get("/api/sessions/{session_id}/export")
    def export_session_endpoint(session_id: int, format: str = "markdown"):
        conn = connect()
        try:
            exists = conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail="Session not found")
            messages = session_store.load_messages(conn, session_id)
        finally:
            conn.close()

        if format == "json":
            content = render_json(session_id, messages)
            media_type = "application/json"
            filename = f"session-{session_id}.json"
        elif format == "markdown":
            content = render_markdown(session_id, messages)
            media_type = "text/markdown"
            filename = f"session-{session_id}.md"
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use json or markdown.")

        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.put("/api/profile")
    def update_profile(body: ProfileUpdate):
        conn = connect()
        try:
            for key, value in body.values.items():
                if key.strip():
                    session_store.set_profile_value(conn, key.strip(), value.strip())
            return {"profile": session_store.get_profile(conn)}
        finally:
            conn.close()

    @app.post("/api/chat")
    def chat_endpoint(body: ChatRequest):
        text = body.message.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Message must not be empty")
        guardrail = inspect_user_input(text)
        if not guardrail.allowed:
            raise HTTPException(status_code=400, detail=guardrail.message)
        identity = identity_for(body.persona)
        model = body.model or config.model

        def events() -> Iterator[str]:
            conn = connect()
            try:
                if not conn.execute(
                    "SELECT 1 FROM sessions WHERE id = ?", (body.session_id,)
                ).fetchone():
                    yield _sse({"type": "error", "message": "Session not found"})
                    return

                history = session_store.load_messages(conn, body.session_id)
                system_prompt = build_system_prompt(
                    session_store.get_profile(conn), [MEMORY_INSTRUCTIONS], identity=identity
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    *[m for m in history if m["role"] != "system"],
                    {"role": "user", "content": text},
                ]

                usage: dict = {}
                reply_chunks: list[str] = []
                try:
                    messages = resolve_tool_calls(
                        conn, config.ollama_url, model, messages, options=config.options
                    )
                    for sanitized_chunk in stream_sanitized_output(
                        stream_chat(config.ollama_url, model, messages, usage, options=config.options)
                    ):
                        reply_chunks.append(sanitized_chunk)
                        yield _sse({"type": "token", "content": sanitized_chunk})
                except (OllamaConnectionError, OllamaModelError) as exc:
                    yield _sse({"type": "error", "message": str(exc)})
                    return

                reply = "".join(reply_chunks)
                session_store.save_message(conn, body.session_id, "user", text)
                session_store.save_message(conn, body.session_id, "assistant", reply)
                yield _sse({"type": "usage", **usage})
                yield _sse({"type": "done"})
            finally:
                conn.close()

        return StreamingResponse(events(), media_type="text/event-stream")

    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="sensai-web", description="Sensai web interface")
    parser.add_argument("--model", help="Ollama model name (overrides config file)")
    parser.add_argument(
        "--temperature", type=float, default=None, help="Sampling temperature (overrides config file)"
    )
    parser.add_argument(
        "--num-ctx", type=int, default=None, help="Context window size in tokens (overrides config file)"
    )
    parser.add_argument("--config", default=None, help="Path to a JSON config file")
    parser.add_argument("--db", default=db.DEFAULT_DB_PATH, help="Path to the SQLite database")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config, args.model, args.temperature, args.num_ctx)
    except ConfigError as exc:
        print(f"[error] {exc}")
        return
    uvicorn.run(create_app(config, args.db), host=args.host, port=args.port)
