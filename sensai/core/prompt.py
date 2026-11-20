BASE_IDENTITY = "You are Sensai, a helpful personal assistant."


def build_system_prompt(
    profile: dict[str, str],
    feature_instructions: list[str],
    identity: str | None = None,
) -> str:
    parts = [identity or BASE_IDENTITY, *feature_instructions]
    if profile:
        profile_lines = "\n".join(f"- {key}: {value}" for key, value in profile.items())
        parts.append(f"Known user profile:\n{profile_lines}")
    else:
        parts.append("No user profile is set yet.")
    return "\n\n".join(parts)
