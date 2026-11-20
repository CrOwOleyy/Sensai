from sensai.core.prompt import build_system_prompt


def test_empty_profile_is_stated():
    prompt = build_system_prompt({}, [])
    assert "No user profile is set yet." in prompt


def test_profile_entries_are_listed():
    prompt = build_system_prompt({"name": "Leyy"}, [])
    assert "- name: Leyy" in prompt


def test_feature_instructions_are_included():
    prompt = build_system_prompt({}, ["Use the memory tools."])
    assert "Use the memory tools." in prompt


def test_default_identity_when_none():
    prompt = build_system_prompt({}, [])
    assert "You are Sensai" in prompt


def test_custom_identity_replaces_default():
    prompt = build_system_prompt({}, [], identity="You are CodeMentor, a mentor.")
    assert "You are CodeMentor, a mentor." in prompt
    assert "You are Sensai" not in prompt
