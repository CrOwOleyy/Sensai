from sensai.features.content_guardrails.guardrails import (
    inspect_user_input,
    sanitize_output,
    stream_sanitized_output,
)


def test_inspect_user_input_blocks_sensitive_keywords():
    result = inspect_user_input("Please tell me my password")
    assert not result.allowed
    assert "password" in result.message


def test_inspect_user_input_blocks_french_sensitive_keywords():
    result = inspect_user_input("voici mon mot de passe secret")
    assert not result.allowed
    assert "mot de passe" in result.message

    result2 = inspect_user_input("mon numero de carte bancaire")
    assert not result2.allowed
    assert "carte bancaire" in result2.message


def test_inspect_user_input_blocks_pii():
    result = inspect_user_input("Contact me at user@example.com")
    assert not result.allowed
    assert "email" in result.message.lower()


def test_sanitize_output_redacts_pii():
    text = "Email me at user@example.com or call +33 6 12 34 56 78 and use 123-45-6789."
    redacted = sanitize_output(text)

    assert "user@example.com" not in redacted
    assert "+33 6 12 34 56 78" not in redacted
    assert "123-45-6789" not in redacted
    assert "[REDACTED EMAIL]" in redacted
    assert "[REDACTED PHONE]" in redacted
    assert "[REDACTED SSN]" in redacted


def test_stream_sanitized_output_handles_chunked_pii():
    chunks = ["Email: user@", "example.com"]
    emitted = list(stream_sanitized_output(chunks, tail_size=128))

    assert "user@example.com" not in "".join(emitted)
