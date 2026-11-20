# [EV2] Content & Privacy Guardrails

## What It Does

Provides multi-layer security and privacy filters for both incoming user inputs and outgoing model generations.

1. **Input Interceptor (`inspect_user_input`)**:
   - Detects sensitive credentials and keywords (passwords, private keys, API tokens, credit cards, bank account info, SSN / NIR) in English and French.
   - Detects email addresses, phone numbers, and payment cards.
   - Rejects malicious or leaking prompts before they ever reach the Ollama API or database history.

2. **Output Sanitizer (`sanitize_output` & `stream_sanitized_output`)**:
   - Monitors model responses in real-time streaming using a sliding window buffer.
   - Automatically redacts PII leaks (emails replaced by `[REDACTED EMAIL]`, phone numbers replaced by `[REDACTED PHONE]`, social security numbers replaced by `[REDACTED SSN]`, cards replaced by `[REDACTED CARD]`).
   - Ensures that only sanitized text is displayed to the user and persisted in SQLite session storage.

## Architecture

```
User Input ──▶ [ inspect_user_input ] ──┬──▶ (Blocked? Abort & warn)
                                        └──▶ Pass to Ollama

Ollama Tokens ──▶ [ stream_sanitized_output ] ──▶ Display & Save Clean Text
```

