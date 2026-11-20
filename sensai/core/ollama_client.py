import json
from collections.abc import Iterator

import requests


class OllamaConnectionError(Exception):
    pass


class OllamaModelError(Exception):
    pass


def _post(
    base_url: str,
    model: str,
    messages: list[dict],
    stream: bool,
    tools: list[dict] | None,
    format_: dict | str | None = None,
    options: dict | None = None,
):
    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {"model": model, "messages": messages, "stream": stream}
    if tools:
        payload["tools"] = tools
    if format_ is not None:
        payload["format"] = format_
    if options:
        payload["options"] = options

    try:
        response = requests.post(url, json=payload, stream=stream, timeout=60)
    except requests.exceptions.ConnectionError as exc:
        raise OllamaConnectionError(
            f"Could not connect to Ollama at {base_url}. Is it running?"
        ) from exc

    if response.status_code == 404:
        raise OllamaModelError(f"Model '{model}' is not available on the Ollama server.")
    if response.status_code != 200:
        raise OllamaConnectionError(
            f"Ollama returned an unexpected status: {response.status_code} {response.text}"
        )
    return response


def chat(
    base_url: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    format_: dict | str | None = None,
    options: dict | None = None,
) -> dict:
    response = _post(
        base_url, model, messages, stream=False, tools=tools, format_=format_, options=options
    )
    body = response.json()
    if error := body.get("error"):
        raise OllamaModelError(error)
    return body["message"]


def stream_chat(
    base_url: str,
    model: str,
    messages: list[dict],
    usage: dict | None = None,
    options: dict | None = None,
) -> Iterator[str]:
    response = _post(base_url, model, messages, stream=True, tools=None, options=options)

    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        if error := chunk.get("error"):
            raise OllamaModelError(error)
        content = chunk.get("message", {}).get("content", "")
        if content:
            yield content
        if chunk.get("done"):
            if usage is not None:
                usage["prompt_tokens"] = chunk.get("prompt_eval_count", 0)
                usage["completion_tokens"] = chunk.get("eval_count", 0)
            break


def list_models(base_url: str) -> list[str]:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise OllamaConnectionError(
            f"Could not connect to Ollama at {base_url}. Is it running?"
        ) from exc
    return sorted(m["name"] for m in response.json().get("models", []))
