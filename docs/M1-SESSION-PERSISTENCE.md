# [M1] Session Persistence & Profiles

## What It Does

Saves your conversation history and user preferences so they survive across CLI restarts.

### The Two Parts

1. **Session Persistence** → full conversation history (every message you send, every response)
2. **Profiles** → persistent user metadata (name, preferences, goals)

## How It Works

### 1. Session Persistence

```
CLI starts
  ↓
Check: does --resume flag exist?
  ├─ YES → fetch last session_id from DB
  │        load all messages from that session
  └─ NO  → create new session_id
```

**Code flow:**

```python
# In sensai/core/cli.py
if args.resume and (session_id := session_store.get_latest_session_id(conn)) is not None:
    messages = session_store.load_messages(conn, session_id)
    print(f"Resuming session #{session_id}")
else:
    session_id = session_store.create_session(conn)
    messages = []  # fresh session

# Then, for every message:
session_store.save_message(conn, session_id, "user", user_input)
# ... get response ...
session_store.save_message(conn, session_id, "assistant", reply)
```

**Database:**

```sql
-- sensai/features/session_persistence/store.py

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,           -- "user" or "assistant"
    content TEXT NOT NULL,         -- the actual message
    created_at TEXT NOT NULL
);
```

**Example database state after two sessions:**

```
sessions:
  id=1, created_at=2026-10-03T16:00:00
  id=2, created_at=2026-10-03T16:30:00

messages (session 1):
  id=1, session_id=1, role=user, content="hello"
  id=2, session_id=1, role=assistant, content="hi there"

messages (session 2, currently active):
  id=3, session_id=2, role=user, content="what was I talking about?"
  id=4, session_id=2, role=assistant, content="I don't have context from your previous session..."
```

### 2. Profiles

```
CLI starts with --set-profile name=Younes
  ↓
Write to profile table: (key="name", value="Younes")
  ↓
Load all profile entries
  ↓
Inject into system prompt: "Known user profile: - name: Younes"
```

**Code flow:**

```python
# In sensai/core/cli.py
for entry in args.set_profile:
    key, _, value = entry.partition("=")
    session_store.set_profile_value(conn, key.strip(), value.strip())

# Then load and inject:
profile = session_store.get_profile(conn)
system_prompt = build_system_prompt(profile, [MEMORY_INSTRUCTIONS])
```

**Database:**

```sql
CREATE TABLE profile (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

**Example:**

```
profile table:
  key="name", value="Younes"
  key="goal", value="learn AI"
  key="language", value="French"

Injected into system prompt:
  "Known user profile:
   - name: Younes
   - goal: learn AI
   - language: French"
```

## Usage

### First Session (New Profile)

```bash
python -m sensai \
  --set-profile name=Younes \
  --set-profile goal="learn AI" \
  --set-profile language=French
```

→ Creates session #1, stores profile, enters chat loop.

### Resume Session

```bash
python -m sensai --resume
```

→ Loads session #N (most recent), loads profile, reconstructs conversation.

### Change Profile (Persists Across Sessions)

```bash
python -m sensai --set-profile language=English --resume
```

→ Updates profile, resumes session. Now language=English is known.

## Real Example

**Session 1:**
```
$ python -m sensai --set-profile name=Younes
Sensai chatbot — model: llama3.2 (type 'exit' to quit)

You: I'm allergic to penicillin
Assistant: Got it, I'll remember that.

You: exit
```

→ Stored:
- session_id=1, profile={name: Younes}, messages=[(user: "I'm allergic...", assistant: "Got it...")]

**Session 2 (same day, later):**
```
$ python -m sensai --resume
Resuming session #1 (2 prior messages)
Sensai chatbot — model: llama3.2 (type 'exit' to quit)

You: What allergies do I have?
Assistant: You mentioned you're allergic to penicillin.

You: exit
```

→ The assistant **had context** from session 1 without you repeating yourself.

## Implementation Details

### Store Functions

All in `sensai/features/session_persistence/store.py`:

```python
def create_session(conn: sqlite3.Connection) -> int
    # INSERT INTO sessions, return session_id

def get_latest_session_id(conn: sqlite3.Connection) -> int | None
    # SELECT id FROM sessions ORDER BY id DESC LIMIT 1

def save_message(conn, session_id: int, role: str, content: str)
    # INSERT INTO messages (session_id, role, content, created_at)

def load_messages(conn, session_id: int) -> list[dict]
    # SELECT role, content FROM messages WHERE session_id ORDER BY id
    # Return: [{"role": "user", "content": "..."}, ...]

def get_profile(conn) -> dict[str, str]
    # SELECT key, value FROM profile
    # Return: {"name": "Younes", "goal": "..."}

def set_profile_value(conn, key: str, value: str)
    # INSERT OR UPDATE profile (key, value)
```

### No Automatic Cleanup

Messages and profiles are never deleted unless you manually modify the DB. This is intentional — they're persistent.

To start fresh, just don't use `--resume`, or delete `sensai.db`.

## Limitations

- Profile updates (`--set-profile name=Different`) overwrite the old value.
- No multi-user support — one `sensai.db` = one user's memory.
- No encryption — the DB is plain SQLite, readable in a text editor (well, binary, but tools can extract it).

## Related Features

- **[M3] Structured Memory** — works *with* session persistence to store lasting facts.
  - Session = raw chat history for context
  - Facts = structured data the model actively manages
