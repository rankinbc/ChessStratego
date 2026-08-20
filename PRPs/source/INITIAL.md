<!--
  INITIAL.md — per-feature intake for /generate-prp.

  Filled by /new-feature on 2026-08-20. Run `/generate-prp` (no argument) to
  research and write the PRP at PRPs/<slug>.md, then
  `/execute-prp PRPs/<slug>.md` to build it.
-->

## FEATURE

Basic computer opponent ("bot") for ChessStratego with three selectable difficulties.
The host seats 1-3 bots from the lobby ("Add bot" with an easy / normal / hard picker;
any mix of humans + bots up to 4 seats, so 1-human-vs-1-bot works and so do 3-4 player
mixed games). Bots auto-arrange their army when setup begins, then play autonomously
with a ~0.5-1.5s think delay per move. Every difficulty plays FAIR: evaluators only
consume the same redacted view a human in that seat would get — opponent stratego ranks
are unknown until combat reveals them. Difficulties:

- **easy** — random legal move with a mild capture preference; blunders freely.
- **normal** — 1-ply lookahead: score each legal move by immediate material outcome
  (value captured vs own piece risked), avoid obviously hanging pieces, protect own
  flag/king.
- **hard** — normal's evaluator plus expected-value scoring against hidden defenders
  (probability-weighted over the publicly-known remaining-piece composition), threat
  awareness for its own flag/king approaches, and capture-exchange peek (does the
  square get retaken next ply). Still redacted-fair, still one move per turn.

Bot moves flow through the normal engine validation + broadcast pipeline, so human
clients need no changes beyond the lobby picker and a bot tag in the player list.

## COMPONENTS

### COMPONENT: game_server

**Purpose**: Extend — new bot decision module (e.g. `app/bot.py`, pure and
transport-free like the engine, but NOT under `app/engine/` since a bot is a player,
not a rule) exposing one interface with three evaluator implementations keyed by
difficulty; a new `add_bot` client message (host-only, lobby phase, difficulty in
payload); bot seating in the room; and a turn-trigger that schedules the bot's move
whenever a broadcast leaves a bot as current player.

**Inputs**: None new

**Outputs**: None new (bot games produce normal match logs; log each bot's difficulty)

**Notes**: Movement legality is fully position-based (public info), so the bot may use
`engine.movement.legal_moves()` directly; only combat OUTCOMES depend on hidden types.
For evaluation every difficulty receives `redact_for_player(state, bot_id)` output —
hidden defenders have `type: null` and must be scored as unknowns, never by peeking at
the real state.

### COMPONENT: game_client

**Purpose**: Extend — lobby gains a host-only "Add bot" control with an easy / normal /
hard choice (hidden once 4 seats filled); player lists show the bot and its difficulty,
e.g. "Bot Ada (hard)". No other UI changes: bot moves arrive as ordinary snapshots.

**Inputs**: None new

**Outputs**: None new

## SHARED DOCUMENTATION

- `CLAUDE.md` — game_server gotchas (redaction boundary, room lock, single-process)
- `PRPs/archive/2026-08-20_v1_chess_stratego.md` — v1 architecture the bot hooks into
- `components/game_server/app/redaction.py` + `tests/test_redaction.py` — the fairness
  boundary the bot must sit behind

## OTHER CONSIDERATIONS

- **Fairness is security-adjacent**: bot evaluators must only ever receive the redacted
  dict, never `GameState`. Add a test that every difficulty's decision function
  operates on a payload whose hidden types are `None` (same shape `test_redaction.py`
  asserts) — cheating must be structurally impossible, not just avoided.
- **Hard tier scope guard**: hard = better evaluation, NOT deep search. No minimax
  tree, no move-time above ~50ms of compute; if it can't be kept inside that budget,
  ship easy+normal and flag hard for a follow-up rather than blocking the build.
- **Asyncio discipline**: think delay = `asyncio.sleep` inside a scheduled task, never
  a blocking sleep; state mutation + broadcast under the room's lock like every other
  mutation. Guard against double-scheduling a bot turn (one pending task per room max).
- **Trigger points**: a bot may become current player after a human move, another bot's
  move, an elimination, or a turn-skip — trigger off every broadcast, not just human
  moves.
- **Bot-vs-bot runaway**: if all humans disconnect, pause bot moves (resume when a
  human reconnects) so abandoned rooms don't burn CPU writing endless match logs.
- **Difficulty sanity check**: add a test that plays hard-vs-easy over a handful of
  seeded games and asserts hard wins the majority — guards against evaluators being
  accidentally identical or inverted.
- **No rule changes**: bots are players, not rules — no `app/engine/` edits, no
  RULES.md section, no DECISION_LOG row.
- Bots need names ("Bot Ada", "Bot Boris"...), are always `connected`, and mint no
  reconnect token.
