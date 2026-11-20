# Sensai — User Stories & Scenario Framing

## Unified Scenario: The Hogwarts Magical Tutor

**Target User**: A first-year Hogwarts student (Gryffindor house) preparing for their end-of-year exams in Potions, Transfiguration, and Charms. The student needs an interactive, private local tutor that adapts its teaching style to different Hogwarts professors (Snape, McGonagall, Dumbledore, Hagrid), remembers personal learning facts across terms, and produces formatted magical reference sheets.

### Design Trade-offs & Abandoned Paths (Traceability)
- **Abandoned Japanese Teacher & Generic Code Mentor**: Early iterations explored Japanese language drills and generic Python mentoring simultaneously. This split focus weakened both use cases. We deliberately unified the system around a single cohesive scenario (Hogwarts Magical Tutor) where persona switching, factual memory (potions, allergies, house affiliation), and strict schema formatting serve a genuine pedagogical goal.
- **Abandoned LLM Frameworks (LangChain / LlamaIndex)**: Excluded in favor of a zero-dependency architecture using direct HTTP calls to Ollama. This guarantees full transparency over the prompt pipeline, predictable latency, and zero abstraction leaks.
- **Abandoned Semantic Summarization [M2] in favor of External Structured Memory [M3]**: Condensing sliding-window conversation turns into fuzzy summaries introduced risk of hallucination on exact student facts. We opted for deterministic SQLite CRUD storage driven by tool calls, ensuring 100% exact retrieval for crucial facts.

---

Format: `As a <type of user>, I want to <action>, so that <outcome>.`  
Every implemented feature includes at least two testable user stories with observable acceptance criteria.

---

## Base — Functional CLI Chatbot [B1]

**As a** first-year Hogwarts student studying late in the common room,  
**I want to** send questions to the local tutor and see the magical instruction stream token by token,  
**so that** I get immediate feedback without waiting for long paragraphs to complete.

Acceptance criteria:
- Response tokens are printed progressively as they arrive from Ollama, not buffered in a single block.
- The command prompt returns cleanly to `You:` once generation finishes.
- An empty message is rejected with a helpful prompt to retry; no request is dispatched to the model.

**As a** student asking multi-part questions about spell incantations,  
**I want to** have my prior turns remembered within the ongoing study session,  
**so that** the tutor understands follow-up questions without me repeating the spell name.

Acceptance criteria:
- A follow-up question referencing an earlier turn (e.g., "And what wand movement accompanies it?") receives a contextually accurate reply.
- Full in-session conversation history is formatted and passed on every subsequent turn.
- Launching the CLI without `--resume` initializes a fresh session with clean context.

---

**As a** student running the assistant on my own machine, **I want to** adjust the temperature and the
context size without editing the code, **so that** I can choose between consistent or more varied answers
and fit long revision sessions to my available memory.

Acceptance criteria:
- `temperature` and `num_ctx` in `config.json` apply to the CLI and the web UI
- `--temperature` and `--num-ctx` take priority over the file, including a temperature of `0`
- The same values are sent on every model call of a turn (tool rounds, streaming, `--schema` mode)
- An invalid value is reported at startup, without a traceback and before any model call

## Memory & Context — Session Persistence & Profiles [M1]

**As an** apprentice returning to the library after classes,  
**I want to** resume my previous study session from the terminal,  
**so that** I can pick up my coursework right where I left off without re-explaining my progress.

Acceptance criteria:
- `python -m sensai --resume` reloads the most recent session and displays the loaded message count.
- New questions asked in the resumed session are appended chronologically to the stored history in SQLite.
- Running without `--resume` creates a new distinct session entry in the database.

**As a** newly sorted Hogwarts student,  
**I want to** record my house and wand specifications in my persistent profile once,  
**so that** every professor immediately knows my background across all future sessions.

Acceptance criteria:
- `--set-profile house=Gryffindor wand="Holly, Phoenix feather"` persists the entries into the `profile` table.
- All stored profile entries are systematically injected into the system prompt at initialization.
- Profile entries persist across restarts without needing to be re-passed on each execution.

---

## Memory & Context — External Structured Memory [M3]

**As a** student with physical sensitivities handling hazardous potion ingredients,  
**I want** the assistant to autonomously record durable safety facts about me (such as an allergy to toad saliva),  
**so that** any professor automatically warns me during future recipe preparation without requiring reminders.

Acceptance criteria:
- When a durable personal fact is mentioned in dialogue, the model triggers the `remember_fact` tool call.
- The key/value pair is persisted into the SQLite `facts` table with accurate timestamps.
- A future query concerning a potion utilizing that ingredient triggers `recall_fact` and includes a customized safety warning.
- The stored fact survives complete program restarts and is accessible across sessions.

**As an** apprentice whose potion tolerances have changed after medical treatment,  
**I want to** instruct the assistant to update or erase an outdated personal fact,  
**so that** obsolete warnings no longer interfere with advanced curriculum lessons.

Acceptance criteria:
- Telling the assistant to update a known fact overwrites the existing row value in the `facts` table.
- Requesting the tutor to forget a fact executes `forget_fact` and removes the row from SQLite.
- Calling `recall_fact` on an erased key returns a clear "not found" status without raising an unhandled exception.

---

## Tools — Structured Output [T5]

**As a** student compiling a standardized personal Herbology grimoire,  
**I want to** constrain the assistant's descriptions into a strict JSON Schema,  
**so that** every botanical entry has exact, machine-readable properties (name, danger level, antidote).

Acceptance criteria:
- Passing `--schema schemas/person.json` constrains Ollama responses strictly to the supplied schema structure.
- The output is validated on the client side against the schema; invalid JSON structures trigger a clean error message.
- A missing or malformed schema file halts execution gracefully before the chat session starts.

**As an** apprentice building a catalog of magical creatures for Care of Magical Creatures class,  
**I want to** generate structured specimen profiles from brief natural-language notes,  
**so that** my index remains uniform and parsable by external study tools.

Acceptance criteria:
- Prompting with informal notes generates a JSON object containing all required fields.
- Undeclared properties are rejected when `additionalProperties: false` is enforced.
- Each validated structured output is saved into the session history like standard dialogue turns.

---

## UX & Lifecycle — Web UI [X1]

**As a** Hogwarts student revising on a portable terminal in the Great Hall,  
**I want to** interact with the tutor through a clean browser interface,  
**so that** I can study without needing command-line syntax.

Acceptance criteria:
- Executing `python -m sensai.features.web_ui` hosts the interactive chat interface at `http://127.0.0.1:8000`.
- Responses stream token by token in real time within the active message container.
- Past conversation logs are displayed in the sidebar and can be resumed with their complete history.
- Backend Ollama interruptions display a non-destructive error alert in the chat window.

**As a** student consulting different department heads during revision,  
**I want to** switch between Professor Snape and Professor Dumbledore from the browser mid-conversation,  
**so that** I can compare a strict disciplinary answer with a broad philosophical perspective on the same problem.

Acceptance criteria:
- The persona selector lists all available faculty configurations from `personas/` (`dumbledore`, `snape`, `mcgonagall`, `hagrid`).
- Switching the persona takes effect immediately on the subsequent turn.
- Preceding conversation turns are preserved across switches, allowing the new professor to reference earlier remarks.
- Real-time token consumption metrics (prompt, completion, total) are updated below each generated response.

---

## UX & Lifecycle — Conversation Export [X3]

**As a** diligent student preparing revision binders for the O.W.L. exams,  
**I want to** export my study conversation as a structured Markdown document,  
**so that** I can print or read my study notes offline.

Acceptance criteria:
- The `/export markdown PATH` command exports the active dialogue into a well-formatted Markdown file.
- Turns are ordered chronologically with clear speaker attributions.
- Internal hidden system prompts and tool-call mechanics are stripped from the exported document.

**As an** apprentice sharing research logs with classmates,  
**I want to** export the full session history as clean JSON,  
**so that** our study group can import dialogue data into shared archives.

Acceptance criteria:
- The `/export json PATH` command outputs the full session metadata, identifiers, and turn history.
- The JSON structure validates against the export schema and omits raw internal system instructions.

---

## Persona — Configurable Agent Profiles [A5]

**As a** student who requires strict discipline to master Potions theory,  
**I want to** launch the tutor configured with Professor Snape's persona by default,  
**so that** my study sessions immediately enforce exacting standards and critical feedback.

Acceptance criteria:
- Setting `"persona": "snape"` in `config.json` initializes the tutor with Professor Snape's behavioral guidelines.
- The persona's system prompt instructions are loaded prior to the first turn, ensuring the opening reply is authentically in character.
- The assistant adopts Snape's sharp, incisive tone while still providing accurate pedagogical guidance.

**As a** student transitioning from theory to hands-on creature care,  
**I want to** switch dynamically from Professor McGonagall to Hagrid during the live chat,  
**so that** the teaching tone shifts from rigorous academic precision to warm, practical field advice.

Acceptance criteria:
- Entering `/persona hagrid` in the CLI switches the active identity for the next turn.
- The conversation context remains uninterrupted, enabling Hagrid to comment on McGonagall's previous instruction.
- The linguistic markers, vocabulary, and temperament visibly change between personas on identical topics.

---

## Safety — Content & Privacy Guardrails [EV2]

**As a** young student sharing spell journals on shared common-room workstations,  
**I want** the tutor to prevent accidental entry of sensitive personal credentials or restricted information,  
**so that** confidential data is not transmitted or retained in local storage.

Acceptance criteria:
- Inputs containing credit card numbers, personal identification codes, or access passwords are intercepted and blocked before dispatch.
- Blocked messages produce a clear explanatory safety notification and are not committed to conversation history.

**As a** safety-conscious student reviewing generated study guides,  
**I want** the tutor to sanitize any sensitive contact details or identifiers from generated outputs,  
**so that** exported study notes remain safe to distribute among study groups.

Acceptance criteria:
- Generated responses containing email addresses or phone patterns are automatically masked with `[REDACTED]` markers.
- Sanitized text is streamed cleanly to the user and accurately recorded in the session store.
