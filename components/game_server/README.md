# game_server

**Purpose**: Real-time multiplayer server for ChessStratego — a hybrid chess+stratego board game, 2-4 players on their own devices joining via a shared link, no accounts. Server-authoritative: every move is validated by a pure rules engine, and outbound state snapshots are redacted per-player so unrevealed Stratego piece ranks never leak to opponents.

**Inputs**: None (self-contained)

**Outputs**: `output/game_server/<YYYY-MM-DD>_<run-description>/` (playtest match logs)

**Pattern**: `api.md` (adapted — websocket game server, not CRUD: no SQLAlchemy, no Alembic, no DB, no JWT/passlib)

**Stack**: Python 3.11+, FastAPI, Pydantic v2, uvicorn, pytest + pytest-asyncio

## How to run

```
pip install -r components/game_server/requirements.txt
cd components/game_server
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000` — this also serves the sibling `game_client` component's static files.

## Structure

- `app/engine/` — pure, transport-free rules engine (no FastAPI imports). One module per rule domain: `board.py`, `pieces.py`, `movement.py`, `combat.py`, `win_conditions.py`, `state.py`. Current rules and documented variants live in each module's docstring.
- `app/rooms.py` — module-level in-memory `GameRoom` registry (single-process, single-worker only), one `asyncio.Lock` per room.
- `app/redaction.py` — `redact_for_player(state, player_id)`, the pure function every outbound snapshot must pass through.
- `app/messages.py` — the `{type, payload, seq}` websocket message envelope.
- `app/routes/lobby.py` — `POST /games` to create a lobby and get a shareable link.
- `app/routes/websocket.py` — `/ws/{game_id}`, the live game connection.
- `app/match_log.py` — writes playtest match logs to the project's `output/` folder.
- `app/main.py` — FastAPI app: routers + mounts `game_client` as static files.
- `tests/` — `test_engine/` (per-module unit tests), `test_redaction.py` (THE security test — no unrevealed opponent rank may appear in any payload), `test_ws/` (lobby + websocket integration via TestClient).

Run the suite from this directory: `python -m pytest -q tests/`

Note: if port 8000 is taken on your machine, any other port works, e.g. `--port 8765`. For LAN play bind `--host 0.0.0.0` and share the LAN address. Never use `--workers > 1` or `--reload` (see CLAUDE.md gotchas).

---

**To extend this component**: edit `PRPs/source/INITIAL.md` and run `/generate-prp`. Don't modify files here directly for new work — let the PRP drive it.
