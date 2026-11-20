from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
import re

INPUT_BLOCK_KEYWORDS = (
    "password",
    "mot de passe",
    "credit card",
    "carte de crédit",
    "carte bancaire",
    "card number",
    "social security",
    "sécurité sociale",
    "ssn",
    "private key",
    "clé privée",
    "cle privee",
    "api key",
    "clé api",
    "cle api",
    "token",
    "secret",
    "bank account",
    "compte bancaire",
    "rib",
    "iban",
)

EMAIL_RE = re.compile(r"(?<![\w.-])([\w.+-]+)@([\w.-]+\.[A-Za-z]{2,})(?![\w.-])")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    message: str | None = None


def inspect_user_input(text: str) -> GuardrailResult:
    normalized = text.casefold()
    for keyword in INPUT_BLOCK_KEYWORDS:
        if keyword in normalized:
            return GuardrailResult(
                allowed=False,
                message=f"Blocked by guardrails: please avoid sharing or requesting sensitive data related to '{keyword}'.",
            )

    if EMAIL_RE.search(text):
        return GuardrailResult(
            allowed=False,
            message="Blocked by guardrails: please remove email addresses before sending this message.",
        )

    if SSN_RE.search(text):
        return GuardrailResult(
            allowed=False,
            message="Blocked by guardrails: please remove social security numbers before sending this message.",
        )

    if PHONE_RE.search(text):
        return GuardrailResult(
            allowed=False,
            message="Blocked by guardrails: please remove phone numbers before sending this message.",
        )

    if CARD_RE.search(text):
        return GuardrailResult(
            allowed=False,
            message="Blocked by guardrails: please remove credit card numbers before sending this message.",
        )

    return GuardrailResult(allowed=True)


def sanitize_output(text: str) -> str:
    redacted = EMAIL_RE.sub("[REDACTED EMAIL]", text)
    redacted = SSN_RE.sub("[REDACTED SSN]", redacted)
    redacted = PHONE_RE.sub("[REDACTED PHONE]", redacted)
    redacted = CARD_RE.sub("[REDACTED CARD]", redacted)
    return redacted


def stream_sanitized_output(chunks: Iterable[str], tail_size: int = 128) -> Iterator[str]:
    tail = ""
    for chunk in chunks:
        tail += chunk
        if len(tail) <= tail_size:
            continue
        safe_text = tail[:-tail_size]
        tail = tail[-tail_size:]
        sanitized = sanitize_output(safe_text)
        if sanitized:
            yield sanitized
    final = sanitize_output(tail)
    if final:
        yield final
