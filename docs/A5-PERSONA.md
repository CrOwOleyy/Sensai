# [A5] Persona

## What It Does

Lets the same system behave as different assistants — a different Hogwarts professor each time —
by swapping a **persona**. A persona is a config file (no code changes), and each one has its own
tone and behavior: Snape is curt and docks points for sloppy answers, McGonagall is strict but fair,
Dumbledore answers with guiding questions and warmth, Hagrid is informal and admits what he doesn't
know. You can switch persona **mid-session without losing the conversation**.

## How It Works

```
Persona file (personas/snape.json)
  { name, role, tone, scope }
        ↓ build_identity()
"You are Professor Snape, the Potions Master at Hogwarts. Your tone is curt, sarcastic and impatient
with sloppy thinking. Answer precisely and never pad the answer with pleasantries..."
        ↓ build_system_prompt(profile, feature_instructions, identity=...)
system message at position 0 of the conversation
```

The persona's text **replaces** the default `"You are Sensai, a helpful personal assistant."` line.
Everything else in the system prompt (memory instructions, user profile) stays.

### Startup vs. Runtime Switch

- **Startup:** `--persona snape` loads the persona and builds the first system prompt from it.
- **Runtime:** `/persona mcgonagall` rebuilds the system prompt in place. Crucially, it keeps
  `messages[1:]` (the whole conversation) and only replaces `messages[0]` (the system message):

```python
def _apply_identity(messages, conn, identity):
    system_prompt = build_system_prompt(get_profile(conn), [MEMORY_INSTRUCTIONS], identity=identity)
    body = [m for m in messages if m["role"] != "system"]
    return [{"role": "system", "content": system_prompt}, *body]
```

That's what makes the switch "retain full context" — the new persona can still answer about things
said under the old persona.

## Persona File Format

```json
// personas/snape.json
{
  "name": "Professor Snape",
  "role": "the Potions Master at Hogwarts",
  "tone": "curt, sarcastic and impatient with sloppy thinking",
  "scope": "Answer precisely and never pad the answer with pleasantries. Point out mistakes bluntly before giving the correct approach."
}
```

- `name` **(required)** — the assistant's name
- `role` **(required)** — what it is ("a Japanese language teacher")
- `tone` *(optional)* — how it speaks ("warm and patient")
- `scope` *(optional)* — what it focuses on / how it should respond

`build_identity()` assembles these into one identity line. Only `name` and `role` are mandatory.

## Usage

### Start with a persona

```bash
python -m sensai --persona snape
```

```
Sensai chatbot — model: llama3.2, persona: Professor Snape (type 'exit' to quit)
```

### Switch mid-session

```
You: Remember the number 42.
Assistant: Obviously. I'll remember 42 — try not to make me repeat myself.

You: /persona dumbledore
Switched to persona: Professor Dumbledore (conversation history kept)

You: What number did I ask you to remember?
Assistant: Ah, the number you entrusted to me earlier was 42 — though I wonder, what makes a number
worth remembering in the first place?
```

The second answer comes from the **dumbledore** persona but still knows about "42" from before
the switch — context is preserved, even though the tone changed completely.

### List personas

```
You: /personas
Available personas: default, dumbledore, hagrid, mcgonagall, snape
```

## In-Chat Commands

| Command | Effect |
|---------|--------|
| `/personas` | List persona files in `personas/` |
| `/persona NAME` | Switch to that persona, keeping history |

These commands are handled locally (no model call) — they just rebuild the system prompt.

## Adding a Persona

Drop a JSON file in `personas/`:

```json
// personas/trelawney.json
{
  "name": "Professor Trelawney",
  "role": "the Divination teacher at Hogwarts",
  "tone": "dramatic, mysterious and prone to foreboding asides",
  "scope": "Frame answers as if reading them in a crystal ball. Still give the real, correct answer, but wrap it in a touch of theatrical prophecy."
}
```

Then: `python -m sensai --persona trelawney`, or `/persona trelawney` mid-session. No code change
needed — that's the point of A5.

## Implementation Files

```
sensai/features/persona/
  loader.py        load_persona, list_personas, build_identity, PersonaError
  __init__.py

sensai/core/
  prompt.py        build_system_prompt now accepts an identity override
  cli.py           --persona flag, /persona and /personas commands, _apply_identity helper

personas/
  default.json, snape.json, mcgonagall.json, dumbledore.json, hagrid.json   example personas

tests/features/persona/
  test_loader.py   load/list/build coverage
tests/core/
  test_prompt.py   verifies custom identity replaces the default
```

## Interaction With Other Features

- **Profile ([M1])** and **memory instructions ([M3])** still appear in the system prompt under the
  persona identity — the persona only changes *who* the assistant is, not *what tools* it has.
- Switching persona does not clear the SQLite session, so `--resume` still works afterward.

## Why This Matters (for the keynote)

- **Real-world parallel:** a support system routing to a technical vs. commercial agent; an
  educational platform with one agent per subject — here, one professor per teaching style.
- **The design choice:** personas are plain config files, so a non-developer can add one. The runtime
  switch keeps history, which is the harder (and more impressive) half of the feature.
- **Limitation:** the active persona isn't persisted to the DB yet, so `--resume` restarts on the
  default persona unless you pass `--persona` again. Persisting it via [M1] would be a natural next step.
