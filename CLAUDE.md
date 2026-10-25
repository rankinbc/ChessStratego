# Project: ChessStratego

A real-time, browser-based board game mixing Chess and Stratego for 2-4 players. Each player commands a full chess set (visible to everyone) plus a stratego set (hidden until combat reveals it) on an expanded board with lakes. Players join via a shared link — no accounts. The rules are experimental by design: the engine is modularized one-module-per-rule-domain so a rule change is a one-module edit, not a rewrite.

**Stack**: Python 3.11+ (FastAPI, uvicorn, Pydantic v2, pytest) for `game_server`; zero-dependency vanilla JS (ES modules) + HTML/CSS for `game_client` (no bundler, no package.json); markdown for `rulebook`.

---

## Project structure (STRICT — do not deviate)

```
ChessStratego/
├── CLAUDE.md
├── README.md
├── .claude/               (settings + slash commands)
├── .scaffolding/          (transient scaffolder state — auto-deleted on first successful build)
├── PRPs/                  (implementation plans; archive/ for completed, source/INITIAL.md for intake)
├── components/
│   ├── game_server/       (FastAPI + websockets: pure rules engine, lobby, redaction)
│   ├── game_client/       (vanilla JS board UI, served by game_server)
│   └── rulebook/          (RULES.md + DECISION_LOG.md — living rules doc)
└── output/
    └── game_server/       (playtest match logs, <YYYY-MM-DD>_<desc>/ per run)
```

**Enforcement rules:**
- Components live in `components/<name>/` only — never loose at project root
- This project has **no `data/` folder** — it has no external data inputs. If inputs ever appear, create `data/<source>/` and update this section first
- All outputs land in `output/<component>/<YYYY-MM-DD>_<description>/` — never at project root, never overwriting prior runs
- Never add a new top-level folder without updating this section first
- Never rename `components/`, `output/`, or `PRPs/`

---

## Rule-change workflow (this project's core convention)

The game rules are meant to evolve through playtesting. A rule change is always THREE edits in the same change:

1. Edit the one engine module that implements the rule (`components/game_server/app/engine/<domain>.py`)
2. Update the matching `RULES.md` section (each section has an `Implemented in:` line pointing at its module)
3. Add a row to `components/rulebook/DECISION_LOG.md` (date, what felt broken, rule change, module edited)

Inactive variants stay documented in full in `RULES.md` (they are docs, not dead code) so switching is a label flip + one module edit. Never build a config-flag framework for rules — the user explicitly chose documented, modular code over config switches.

---

## Components

### game_server (api)

**Purpose**: Real-time multiplayer server — pure transport-free rules engine (`app/engine/`, one module per rule domain), per-game websocket rooms, link-based lobby with reconnect tokens, per-player hidden-info redaction, serves game_client statics, writes playtest match logs.
**Inputs**: None
**Outputs**: `output/game_server/<YYYY-MM-DD>_<run-description>/` (playtest match logs)
**How to run**: `cd components/game_server && uvicorn app.main:app --host 127.0.0.1 --port 8000` (then open `http://127.0.0.1:8000`)

**Gotchas:**
- **Redaction is a security boundary, not a UI concern.** Every outbound state snapshot must pass through `redact_for_player()` before hitting the wire. An opponent's unrevealed stratego rank appearing in any payload (including debug logs or error messages) is a security-class bug. Keep `tests/test_redaction.py` green and expand it with every state-shape change.
- **Single-process only.** `app/rooms.py`'s `ROOMS` dict is module-level in-memory state — never run `--workers > 1` or multiple uvicorn processes; game state would silently split across workers.
- **Every websocket receive loop needs `try/except WebSocketDisconnect`** (plus a catch-all for abrupt drops) that removes the dead connection — otherwise the next broadcast throws on a closed socket.
- **`mimetypes.add_type("text/javascript", ".js")` must run before the `StaticFiles` mount** in `app/main.py` — the Windows registry otherwise serves `.js` as `text/plain` and browsers refuse to execute the client modules.
- **No `--reload` during websocket dev on Windows** — restart uvicorn manually instead.
- **`app/engine/` stays pure** — nothing under it may import FastAPI/Starlette/websockets. That purity is what makes rules testable and swappable in isolation.
- **Guard state mutation with the room's `asyncio.Lock`** — even single-threaded asyncio can interleave two players' moves across await points.
- **This component deviates from the standard CRUD api pattern**: no DB, no SQLAlchemy/Alembic, no JWT/passlib, no `.env`. Don't reintroduce those assumptions in future PRPs.

### game_client (form_view)

**Purpose**: Browser board UI — CSS Grid board with lakes, click-to-select / click-to-move (works on phones), phases lobby → secret setup → play → combat reveal → game over, websocket client with backoff reconnect + full-snapshot resync, face-down rendering for redacted opponent pieces.
**Inputs**: None (all state arrives over the websocket)
**Outputs**: None (UI only)
**How to run**: Served by game_server — open `http://127.0.0.1:8000` (never open `index.html` via `file://`; ES modules won't load)

**Gotchas:**
- **`js/protocol.js` is the shared wire contract** — its `MSG` constants and the `{type, payload, seq}` envelope must match game_server's websocket handler exactly. Change them together or not at all.
- **Hidden-info rendering must be null-safe** — opponent stratego pieces arrive redacted (`type: null`, `revealed: false`); the client must never infer or cache identity from positions, prior reveals, or elimination logic.
- **No native HTML5 drag-and-drop** — it has no touch support; tap-tap (click to select, click to move) is the one code path for desktop and phone.
- **Reconnect resyncs from a full snapshot**, never replays/patches missed messages — `seq` detects gaps, it is not a delta-replay mechanism.
- **Zero dependencies is deliberate** — no bundler, no package.json, no CDN references. If a library is ever truly needed, vendor it under `js/vendor/` with a pinned version.

### rulebook (product_doc)

**Purpose**: The living rules document — `RULES.md` (full rules, current rule + documented inactive variants per section, `Implemented in:` pointer to the engine module) and `DECISION_LOG.md` (playtest decision log).
**Inputs**: Playtest experience
**Outputs**: The maintained docs themselves in `components/rulebook/`
**How to run**: Open `components/rulebook/RULES.md`

**Gotchas:**
- **Doc/code lockstep** — see "Rule-change workflow" above; it is this component's reason to exist.
- **All core mechanics are decided** (board, setup, turn order, combat, win conditions, armies, movement). The only open questions left in `RULES.md` are the ones each inactive variant lists for "decide at activation time" (rank-mapping combat, classic check). Rules are decided on paper only until the first logged playtest — treat `DECISION_LOG.md` rows marked "pre-playtest" as tentative.
- **Log rule changes, not playtest sessions** — `DECISION_LOG.md` gets a row when a rule actually changed.

---

## Validation gates

```bash
# game_server
ruff check components/game_server/
mypy components/game_server/app/
pytest -q components/game_server/tests/

# game_client (syntax gate; no JS test framework by design)
for f in components/game_client/js/*.js; do node --check "$f"; done

# Runtime smoke (single worker, no --reload)
cd components/game_server && uvicorn app.main:app --host 127.0.0.1 --port 8765 &
sleep 2 && curl -f http://127.0.0.1:8765/ >/dev/null && echo "OK"
```

---

### Session Start

- **Read `.scaffolding/manifest.json` first if it exists.** Check `lifecycle.stage`:
  - `"plan"` — the v1 implementation plan is written at `PRPs/v1_<slug>.md` but hasn't been executed. Components are stubs. On a fresh session, tell the user "**This project is at stage 1 of 2 (planned). Components are stubs — not yet runnable.** Next step: `/execute-prp PRPs/v1_<slug>.md`." Never suggest running component entry commands; they won't work yet.
  - `"built"` (rare — `/execute-prp` normally deletes `.scaffolding/` on first full build, so this state is only seen mid-partial-build) — some components built, others still stubs. Check individual `scaffold_state` values before claiming the project is ready.
  - `.scaffolding/` missing entirely — the common built-project case. `/execute-prp` cleaned up scaffolder state on first successful build. Treat the project as fully built; entry commands in CLAUDE.md's "How to run" are runnable. Adding new features uses `/generate-prp` (reads `PRPs/source/INITIAL.md`) → `/execute-prp PRPs/<new-slug>.md`.
- If `HANDOFF.md` exists, read it first — a previous session paused mid-work.
- Otherwise, if `PRPs/source/INITIAL.md` is filled in and no PRP exists in `PRPs/` yet, that's the project intent — suggest `/generate-prp` (no arg) as the next step.
- Consult `PRPs/README.md` if the PRP workflow comes up.
- Check `PLANNING.md` / `TASK.md` if they exist.

### Context Discipline

Keep long sessions coherent — follow these automatically.

- **Scout files >400 lines before full-reading.** Grep for the target section first; Read only the slice you need.
- **Dispatch sub-agents for multi-file research and web lookups** (Task tool: Explore, general-purpose, Plan). Don't pollute the main session.
- **Externalize multi-step plans to files.** Write PRPs under `PRPs/`. Plans in files survive context resets; plans in conversation don't.
- **Propose `/handoff` proactively** when context is heavy or the user's about to pause. Don't let long sessions silently degrade.

### Code

- **No file over ~500 lines.** Split when approaching the limit.
- **Organize by feature**, following the language's conventions.
- **Externalize config and secrets** via env vars. Never hardcode credentials.

### Testing

- **Unit tests for new features.** At minimum: one expected-use, one edge case, one failure case.
- **When you change logic**, update affected tests.

### Docs

- **Update `README.md`** when features change or setup changes.
- **Comment the non-obvious why**, not what the code does.

### AI Behavior

- **Ask if uncertain** — don't assume missing context.
- **No hallucinated libraries or APIs** — verify packages exist before using them.
- **Confirm file paths and symbols** before referencing them.
- **Don't delete or overwrite existing code** without explicit instruction.

### Workflow

- **Default to the PRP workflow for new work.** New features, components, or multi-step changes go through `/new-feature` → `/generate-prp` → `/execute-prp`. `/new-feature` is the guided entry point — it interviews the user and fills `PRPs/source/INITIAL.md`; `/generate-prp` researches and writes the PRP; `/execute-prp` builds it. If the user asks for non-trivial new work and no active (non-archived) PRP in `PRPs/` covers it, propose `/new-feature` first and briefly explain why — the validation gates and checkpoints are what keep long sessions coherent across resets. Trivial fixes (typos, one-line bug fixes, doc tweaks, minor refactors) don't need a PRP — just do them.

### Project Cleanliness

- **Respect the project structure** declared at the top of this file. Never create new top-level folders without updating the structure block first. Components live in `components/<name>/`, outputs in `output/<component>/<date>_<description>/`.
- **Tool caches outside the project.** Configure your language's tools to cache under `~/.cache/<tool>/` (or equivalent). For Python: set cache dirs in `pyproject.toml` and `PYTHONDONTWRITEBYTECODE=1`.
- **Descriptive file and folder names.** It should be obvious what's what from the name alone. Avoid `utils.py`, `data.csv`, `temp.txt` — prefer `csv_loader.py`, `sales_2024_q4.csv`, etc.
- **Generated artifacts** always land under `output/<component>/<date>_<description>/` — never at the project root. Other gitignored dirs (`dist/`, `build/`, `htmlcov/`) are fine where a toolchain expects them.
- **Output rotation.** Keep the latest ~5 runs directly under `output/<component>/`. Move older runs to `output/<component>/_archive/` so routine globs and exploration skip historical artifacts. The `_archive/` prefix is intentionally glob-unfriendly for that reason. No script enforces this — apply the convention when you notice a component's output folder growing past ~5 dated subdirectories.
- **PRP lifecycle.** Active plans live in `PRPs/`. On successful `/execute-prp`, the command moves the PRP to `PRPs/archive/<date>_<slug>.md` — don't treat files in `archive/` as current work. Your spec lives at `PRPs/source/INITIAL.md` from scaffold onward; edit it in place for the next feature.
- **Throwaway / single-use files** → prefix with `temp_` so they're easy to find and delete later.
- **Don't create files the user didn't ask for** — no `PLANNING.md`, `NOTES.md`, `TODO.md`, etc. unless requested.

### Task Completion

- **PRP workflow**: validation gates passing = work is done.
- **TASK.md projects**: mark complete immediately; add new sub-tasks under "Discovered During Work".

---

## Stack-specific rules

Python 3.11+ with FastAPI (>=0.115) + uvicorn[standard] (>=0.30) + Pydantic v2 only; test with pytest + pytest-asyncio; lint with ruff, typecheck with mypy. No database, no ORM, no auth libraries in this project. Client is vanilla JS ES modules — no Node toolchain beyond `node --check` / `node --test`. Dev machine is Windows 11: no uvloop (fine), no `--reload` during websocket work, and keep the `.js` mimetype fix in `app/main.py`.
