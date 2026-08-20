name: "ChessStratego v1 — realtime hybrid chess+stratego for 2-4 players"
description: |
  Build the v1 of ChessStratego from the scaffolded stubs: a pure modular rules
  engine, a websocket game server with link-based lobby and hidden-info redaction,
  a zero-dependency browser client, and a rulebook kept in lockstep with the code.

  Run with:
    /execute-prp PRPs/v1_chess_stratego.md                       (full build)
    /execute-prp PRPs/v1_chess_stratego.md --component <name>    (partial build)

---

## Goal

A working v1 where 2-4 players, each on their own device, open a shared link, privately set up their armies (full chess set visible to all + reduced stratego set hidden), and play a complete game in real time — moves validated server-side, hidden pieces revealed only through combat, eliminations and a winner declared — with every rule implemented in exactly one documented engine module so playtest-driven rule changes stay one-module edits.

## Why

- The user wants to playtest a hybrid board game concept with his brother and iterate on rules quickly.
- Rules are experimental: modular, documented code (NOT config flags — explicit user decision) makes "change combat resolution" a single-module edit Claude can perform on request.
- Hidden information makes server authority non-negotiable: the server is referee and secrets-keeper.

## What

- Create game → get short shareable link → 2-4 players join with a display name.
- Secret setup phase: each player arranges pieces in their setup zone; opponents see chess pieces but only face-down placeholders for stratego pieces.
- Turn-based play: click piece → legal targets highlight → click target. Combat reveals participants to everyone. Eliminations on flag/king loss. Last player standing wins.
- Reconnect: dropped player rejoins via their token and receives a full redacted snapshot.
- Match log written to `output/game_server/<date>_<desc>/` per game for playtest review.

### Success Criteria

- [ ] 2-player game fully playable end-to-end on one machine (two browser tabs) and across LAN
- [ ] 3-player and 4-player board layouts and turn order implemented and playable
- [ ] Redaction tests prove no unrevealed opponent stratego rank ever appears in any player's payload
- [ ] Reconnect mid-game restores a correct, correctly-redacted board
- [ ] `RULES.md` matches implemented behavior exactly; open questions closed and logged in `DECISION_LOG.md`
- [ ] All validation gates pass (Levels 1-3 below)
- [ ] `.scaffolding/manifest.json` components flipped to `built` (then `.scaffolding/` deleted per /execute-prp)

## All Needed Context

### Documentation & References

```yaml
- file: CLAUDE.md
  why: Project structure enforcement, rule-change workflow, per-component gotchas — read first

- file: components/rulebook/RULES.md
  why: THE source of truth for game rules. Engine must implement what it says; where it
       marks something open/inferred, resolve using the defaults in this PRP and update it.

- file: components/game_server/README.md
  why: Component orientation + stub map

- file: components/game_client/README.md
  why: Component orientation + manual smoke-test checklist

- url: https://fastapi.tiangolo.com/advanced/websockets/
  why: Canonical connect/receive/broadcast pattern, WebSocketDisconnect handling

- url: https://github.com/fastapi/fastapi/discussions/11298
  why: Practical disconnect-handling patterns for connection managers

- url: https://uvicorn.dev/concepts/event-loop/
  why: Windows Proactor/Selector loop behavior (dev machine is Windows 11)

- url: https://websocket.org/guides/reconnection/
  why: Backoff + full-snapshot-on-reconnect rationale (client ws.js)

- url: https://websocket.org/guides/frameworks/fastapi/
  why: Single-process vs multi-worker broadcast tradeoffs (why single worker only)

- url: https://github.com/Kludex/starlette/discussions/1568
  why: Windows .js MIME bug in StaticFiles + the mimetypes.add_type fix

- url: https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API
  why: Confirms no native touch support — why the client is tap-tap, not drag-drop
```

### Current Codebase tree (post-scaffold; components are stubs)

```
ChessStratego/
├── CLAUDE.md / README.md / .gitignore
├── .claude/  .scaffolding/  PRPs/  output/game_server/
└── components/
    ├── game_server/
    │   ├── README.md  requirements.txt
    │   ├── app/  __init__.py  config.py  main.py  rooms.py  redaction.py
    │   │         messages.py  match_log.py
    │   ├── app/routes/  __init__.py  lobby.py  websocket.py
    │   ├── app/engine/  __init__.py  board.py  pieces.py  movement.py
    │   │               combat.py  win_conditions.py  state.py
    │   └── tests/  __init__.py
    ├── game_client/
    │   ├── README.md  index.html
    │   ├── css/style.css
    │   ├── js/  main.js  state.js  render.js  board.js  ws.js  protocol.js
    │   └── tests/.gitkeep
    └── rulebook/
        ├── README.md  RULES.md  DECISION_LOG.md
```

### Desired Codebase tree (files /execute-prp adds or completes)

```
components/game_server/
├── app/engine/*.py          # all engine stubs become real, pure, tested modules
├── app/rooms.py             # GameRoom: connections, state, lock, broadcast
├── app/redaction.py         # redact_for_player — complete + fuzz-tested
├── app/routes/lobby.py      # POST /games, join-info endpoint
├── app/routes/websocket.py  # /ws/{game_id} full message loop
├── app/match_log.py         # per-game JSONL move/combat log
└── tests/
    ├── test_engine/         # per-module unit tests (board, movement, combat, win)
    ├── test_redaction.py    # THE security test — see Task 4
    └── test_ws/             # lobby + websocket integration via TestClient

components/game_client/
└── js/*.js + css + index.html  # stubs become the working five-phase UI

components/rulebook/
├── RULES.md                 # open sections closed with the defaults below
└── DECISION_LOG.md          # rows for every default this build locks in
```

### Known Gotchas

```python
# --- game_server ---
# CRITICAL: redact_for_player() on EVERY outbound payload. An unrevealed opponent
#   stratego rank on the wire (including logs/errors sent to clients) = security bug.
# CRITICAL: app/engine/ imports nothing from fastapi/starlette/websockets. Pure.
# CRITICAL: single process, single worker. ROOMS is a module-level dict.
# GOTCHA: try/except WebSocketDisconnect (+ broad except for abrupt drops) in every
#   receive loop; remove dead sockets from the room before the next broadcast.
# GOTCHA: asyncio.Lock per GameRoom around all state mutation.
# GOTCHA (Windows): mimetypes.add_type("text/javascript", ".js") BEFORE StaticFiles
#   mount; never use --reload during websocket dev.
# PATTERN: discriminated-union Pydantic envelope {type, payload, seq}; malformed
#   input -> typed error message, never a crashed loop.

# --- game_client ---
# CRITICAL: tap-tap movement only (native drag-drop has no touch support).
# CRITICAL: render redacted pieces null-safely (type: null); never infer identity.
# GOTCHA: full-snapshot resync on reconnect; seq detects gaps, no delta replay.
# GOTCHA: ES modules require http:// — never open index.html from file://.
# PATTERN: js/protocol.js MSG constants are the wire contract shared with the
#   server's messages.py — build both sides from the same list, change together.

# --- project-wide invariants ---
# Rules live in modules, not config flags (explicit user decision).
# Rule change = engine module + RULES.md section + DECISION_LOG.md row, same change.
# Piece-count constraint: full classic stratego set (40) + chess set (16) = 56/player
#   CANNOT fit 2-4 players on a 12x12 board. v1 uses a REDUCED stratego set (below).
```

## Implementation Blueprint

### v1 rule defaults (lock these in; each is playtest-tunable later)

Where `RULES.md` marks a question open, apply these defaults and update the doc +
`DECISION_LOG.md` (date, "v1 default locked by PRP", module). If a default here
contradicts something already decided in `RULES.md`, RULES.md wins — flag it.

- **Board**: scales with player count — 12x12 (2 players), 14x14 (3), 16x16 (4). One tunable table in `board.py` (`BOARD_SIZE_BY_PLAYER_COUNT`); lakes defined per size in the same table (12x12: two 2x2 lakes centered; 14x14/16x16: four 2x2 lakes, symmetric around center). Impassable to everything.
- **Layouts**: 2 players = opposite edges; 3 = three edges (one empty); 4 = all four edges. Setup zone = own edge, 3 rows deep, full width.
- **Army per player**: 16 chess (standard) + 14 stratego: 1 flag, 3 bombs, 1 spy, 2 scouts, 2 miners, 1 marshal, 1 general, 1 colonel, 1 major, 1 captain. 30 pieces fit every setup zone (36 squares at 12x12, 48 at 16x16). Documented inactive variant: full classic 40-piece stratego set — viable at 16x16 with a 4-row setup zone (64 squares ≥ 56 pieces); note it in pieces.py's docstring and RULES.md.
- **Setup**: player places ALL pieces freely inside their setup zone (chess placement is free too — no fixed chess formation on a custom board).
- **Pawns**: move away from own edge ("forward" = toward the opposite edge); promote on reaching the farthest row. Diagonal capture relative to that direction.
- **Turn order**: clockwise from game creator; one move per turn.
- **Combat (current rule — combat.py)**: chess vs chess = normal chess capture. Chess attacks stratego = defender revealed; chess piece wins UNLESS defender is a bomb (bomb destroys the attacker; bombs are only defused by miners, which chess lacks). Stratego attacks chess = attacker revealed; attacker wins. Stratego vs stratego = classic rules (rank compare, spy beats marshal when attacking, miner defuses bombs, equal ranks both die). Documented inactive variant: rank-mapping.
- **Elimination**: lose your flag OR your king → all your remaining pieces are removed; play continues among the rest; last player standing wins. No check/checkmate — the king is captured like any piece.

### Build order

Engine first (pure, fully unit-tested before any transport), then redaction, then the websocket/lobby layer against the tested engine, then the client against a running server, then integration smoke, then rulebook close-out. `rulebook` updates happen alongside each default the build locks in — not as an afterthought.

### Component: game_server (api)

Purpose/Inputs/Outputs/Entry: see CLAUDE.md component section.

```yaml
Task 1 — engine data model:
  MODIFY app/engine/pieces.py, app/engine/state.py:
    - Piece: id, owner, kind (chess/stratego), type, revealed, pos
    - Reduced stratego set + chess set factories per the v1 defaults
    - GameState: board geometry ref, pieces, phase (lobby/setup/playing/finished),
      turn order, per-player status; Pydantic v2 models
Task 2 — board + movement:
  MODIFY app/engine/board.py: size-by-player-count table (12/14/16), lakes per size,
    per-player-count edge layouts, setup zones
  MODIFY app/engine/movement.py: chess moves (pawn direction per edge, promotion),
    stratego moves (1 step; scout = straight-line run; bombs/flag immobile);
    legal_moves(state, piece) -> list[pos]
Task 3 — combat + win + engine tests:
  MODIFY app/engine/combat.py: the current rule above; keep rank-mapping variant
    documented in the docstring with its would-be implementation sketch
  MODIFY app/engine/win_conditions.py: flag/king elimination, last-standing winner
  CREATE tests/test_engine/: expected-use + edge + failure per module
    (lake blocked, scout over gap denied, spy-vs-marshal both directions,
     bomb vs chess attacker, pawn promotion on far row, elimination cascade)
Task 4 — redaction (SECURITY):
  MODIFY app/redaction.py: pure redact_for_player(state, player_id) -> dict;
    unrevealed opponent stratego pieces -> {owner, pos, revealed: false, type: null}
  CREATE tests/test_redaction.py: for randomized states, serialize every player's
    payload and assert no opponent unrevealed type/rank string appears anywhere
Task 5 — rooms + lobby + websocket:
  MODIFY app/rooms.py: GameRoom (connections, GameState, asyncio.Lock, broadcast
    -> per-player redacted snapshots), module ROOMS dict
  MODIFY app/routes/lobby.py: POST /games -> 6-char game_id + join URL;
    reconnect token (uuid4) minted per player on first join, returned once
  MODIFY app/routes/websocket.py: /ws/{game_id} loop — join/rejoin, setup_submit,
    move_request -> engine validation -> mutate under lock -> broadcast snapshots;
    typed error envelope on bad input; WebSocketDisconnect cleanup
Task 6 — match log + statics:
  MODIFY app/match_log.py: JSONL per game under output/game_server/<date>_<game_id>/
    (moves, combats with BOTH identities — server-side file, never sent to clients)
  VERIFY app/main.py: mimetypes fix before StaticFiles mount of components/game_client
Task 7 — ws integration tests:
  CREATE tests/test_ws/: TestClient.websocket_connect — create game, 2 players join,
    setup, a move broadcasts, and player B's payload never contains A's hidden ranks
```

```python
# Task 5 pseudocode — the receive loop shape
async def ws_endpoint(websocket, game_id):
    room = ROOMS.get(game_id)            # typed error + close if missing
    player = await join_or_rejoin(room, websocket)   # reconnect token path
    await send_snapshot(room, player)    # full redacted snapshot on (re)join
    try:
        while True:
            envelope = parse_envelope(await websocket.receive_text())  # Pydantic union
            async with room.lock:                     # GOTCHA: all mutation under lock
                result = apply(room, player, envelope)  # engine validates; never trust client
            await room.broadcast_snapshots()          # CRITICAL: redact_for_player per recipient
    except WebSocketDisconnect:
        room.drop_connection(player)                  # seat + token survive for rejoin
```

Validation (component):
```bash
ruff check components/game_server/ && mypy components/game_server/app/
pytest -q components/game_server/tests/
```

### Component: game_client (form_view)

```yaml
Task 8 — protocol + state + ws:
  MODIFY js/protocol.js: MSG constants mirroring app/messages.py exactly
  MODIFY js/state.js: single state object (phase, you, players, board, selection)
  MODIFY js/ws.js: connect, capped-backoff-with-jitter reconnect, "reconnecting…"
    banner hook, full-snapshot handler, send(type, payload)
Task 9 — board + render:
  MODIFY js/board.js: CSS Grid sized from the snapshot's board dimension (never
    hardcode 12 — board scales with player count), lake squares, aria-labels, tap-tap
    (select own piece -> highlight legal targets from snapshot -> tap to move)
  MODIFY js/render.js: full re-render per phase: lobby (name + join/share link),
    setup (place pieces in zone, submit), play (turn indicator, face-down opponent
    stratego pieces), combat reveal flash, game over
  MODIFY js/main.js + index.html + css/style.css: wire it together; responsive
    aspect-ratio board; readable on a phone
```

Validation (component):
```bash
for f in components/game_client/js/*.js; do node --check "$f"; done
# plus the manual two-tab checklist in components/game_client/README.md
```

### Component: rulebook (product_doc)

```yaml
Task 10 — close the open questions:
  MODIFY RULES.md: fill every "[/execute-prp fills this in]" stub with the v1
    defaults above; verify each section's "Implemented in:" path is real
  MODIFY DECISION_LOG.md: one row per default locked by this build
```

Validation: manual read-through — every RULES.md claim must match engine behavior.

## Validation Loop

### Level 1 — lint + typecheck
```bash
ruff check components/game_server/
mypy components/game_server/app/
for f in components/game_client/js/*.js; do node --check "$f"; done
```

### Level 2 — unit + integration tests
```bash
pytest -q components/game_server/tests/
```

### Level 3 — end-to-end smoke
```bash
cd components/game_server && uvicorn app.main:app --host 127.0.0.1 --port 8000 &
sleep 2
curl -f http://127.0.0.1:8000/ >/dev/null && echo "client served OK"
curl -sf -X POST http://127.0.0.1:8000/games | grep -o '"game_id"' && echo "lobby OK"
# then the manual checklist: two tabs -> create/join -> setup -> move -> combat
# reveal -> confirm tab B never shows tab A's hidden pieces -> kill/restore network
# in one tab -> confirm resync. Log one real playtest game to output/game_server/.
```

## Final validation Checklist

- [ ] Level 1 clean (ruff, mypy, node --check)
- [ ] Level 2 green, including tests/test_redaction.py
- [ ] Server starts single-worker; client loads at http://127.0.0.1:8000 (correct .js MIME)
- [ ] Two-tab manual game completes: setup → moves → combat reveal → elimination → winner
- [ ] Reconnect mid-game restores correct redacted state
- [ ] Match log JSONL written under output/game_server/
- [ ] RULES.md + DECISION_LOG.md updated; every "Implemented in:" path exists
- [ ] .scaffolding/manifest.json flipped to built (then folder deleted by /execute-prp)

## Anti-Patterns to Avoid

- Don't send unredacted state anywhere a client can see it — not in errors, not in logs pushed to clients. The match log file is the only place full identities live.
- Don't build a rules config framework — rules are documented modules by explicit user decision.
- Don't import fastapi/starlette inside app/engine/.
- Don't use native HTML5 drag-and-drop or add a JS build step / npm dependency.
- Don't run uvicorn with --workers > 1 or --reload (Windows websocket dev).
- Don't invent chess/stratego edge-case rules silently — when a case isn't covered by RULES.md or this PRP's defaults, ask the user and log the decision.

## Context pointers

- `CLAUDE.md` — structure enforcement, rule-change workflow, gotchas (read first)
- `components/rulebook/RULES.md` — rules source of truth
- `components/*/README.md` — per-component orientation
- `PRPs/README.md` — PRP workflow reference
