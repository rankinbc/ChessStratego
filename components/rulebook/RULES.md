---
title: ChessStratego — Rules
status: living document (rules evolve through playtest; see DECISION_LOG.md)
last_updated: 2026-10-25
players: 2-4
---

# ChessStratego — Rules

This is the living rules reference for ChessStratego, a hybrid chess + stratego board game for 2-4 players. Rules here are the source of truth for gameplay behavior — when a rule changes, the paired game engine module (see each section's **Implemented in:** line) must be updated to match, and the change logged in `DECISION_LOG.md`.

**Convention**: every rule section below carries an `Implemented in:` line pointing at the exact `game_server` engine module that codes it. If you change a rule, change that one module too — don't let the doc and code drift.

---

## 1. Overview

**Status**: DECIDED

**Implemented in**: N/A (descriptive — no single module; see per-mechanic sections below)

Each player fields two armies on the same board:

- **A full chess set** (16 pieces) — always visible to all players, at all times. Standard chess movement rules apply piece-by-piece (pawn, knight, bishop, rook, queen, king), with mixed-army combat and check rules modified as described below.
- **A reduced stratego set** (14 pieces — see section 8 for the exact composition and why the full 40-piece set does not fit) — hidden from opponents until combat reveals a piece. Classic stratego specialties are retained:
  - **Ranks are numbered classic-style, 1 is the strongest**: Marshal 1, General 2, Colonel 3, Major 4, Captain 5, Miner 8, Scout 9. The lower number wins a fight (see section 8 for the full set).
  - **Scout (9)**: the weakest rank, but may move multiple squares in a straight line across empty squares (like a rook), instead of stratego's usual one-square-per-turn limit.
  - **Miner (8)**: defuses bombs — wins automatically when attacking a Bomb.
  - **Spy (S)**: all-or-nothing. Takes ANY piece it attacks (except a Bomb), and dies to ANY piece that attacks it.
  - **Bombs (B)**: immobile. Destroy any attacker except a Miner — chess pieces included.
  - **Flag (F)**: immobile. Capturing an opponent's flag is one of the two elimination conditions; BOTH the flag and the king must fall to eliminate a player (see Win Conditions).

A player's chess pieces and stratego pieces coexist on the same board and can attack each other — see Combat Resolution for how cross-army combat resolves.

---

## 2. Board

**Status**: DECIDED (v1 defaults locked by the PRP build, 2026-08-20)

**Implemented in**: `components/game_server/app/engine/board.py`

- **Board size scales with player count**: 12x12 (2 players), 14x14 (3), 16x16 (4). One tunable table, `BOARD_SIZE_BY_PLAYER_COUNT`. (The earlier "10x10 or 12x12" framing assumed one fixed size; the scaling table is what makes 3-4 player setup zones fit — see section 8 for the piece-count math.)
- **Lakes** are impassable 2x2 blocks, symmetric around the board center: two blocks at 12x12 (rows 5-6, columns 3-4 and 7-8, 0-indexed), four blocks at 14x14 and 16x16 (`LAKES_BY_SIZE`). Impassable to everything; sliding pieces cannot pass through them; knights may leap over them.
- **Edge layouts**, seated clockwise from the game creator (always south, the bottom of the screen):
  - **2 players**: south / north (opposite edges).
  - **3 players**: south / west / north; east stays empty.
  - **4 players**: all four edges, one army per edge.
- **Setup zone**: your own edge, 3 rows (or columns) deep, full length. Where two occupied zones would overlap in a 3x3 corner, the corner belongs to exactly one of them — a pinwheel rule (NW corner goes to north, NE to east, SE to south, SW to west; a corner bordering an empty edge stays with its occupied neighbor). Every zone holds at least 33 squares, enough for the 30-piece army.
- **Orientation**: the board is NOT rotated per player — everyone sees the same fixed orientation (north at top). "Forward" for pawns is simply the direction away from your own home edge (see section 9).

---

## 3. Setup Phase

**Status**: DECIDED (v1 defaults locked by the PRP build, 2026-08-20)

**Implemented in**: `components/game_server/app/engine/state.py` (validation + auto-place) over the zones defined in `board.py`

- Each player **privately arranges ALL 30 of their pieces** — chess included — anywhere inside their own setup zone. There is no fixed chess formation: a custom board with per-edge armies has no meaningful "standard back rank", so chess placement is as free as stratego placement.
- **No row constraints**: chess and stratego pieces may mix freely within the zone.
- **Privacy flow**: every player is on their own device, so each gets a private screen. During the setup phase, opponents see NOTHING of your placements — not even your chess pieces. When everyone has submitted and play begins, chess pieces (and face-down stratego backs) become visible at their positions. (Stricter than the minimum the rules require — it also hides chess formations until the last player commits, which avoids last-mover information advantage during setup.)
- The client offers **auto-arrange** (server places randomly, flag on the back row, bombs and king deep) as a fast path for casual games; manual tap-tap placement is the default.
- A player may resubmit their setup while others are still placing; the phase flips to play the moment the last player submits.

---

## 4. Turn Order

**Status**: DECIDED (v1 defaults locked by the PRP build, 2026-08-20)

**Implemented in**: `components/game_server/app/engine/movement.py` (`current_player`, `advance_turn`)

- **Strict round-robin, clockwise from the game creator** (south -> west -> north -> east seating). One single piece-move per turn, chess-style.
- **Eliminated seats are skipped** for the rest of the game.
- **A player with no legal move is skipped automatically** (the server broadcasts a `turn_skipped` event) — they are not eliminated; a later capture may unblock them.
- **If no active player can move at all**, the game ends immediately as a **draw** (no winner). This is a near-impossible corner (it requires every mobile piece on every side to be gone or walled in), but the engine handles it rather than deadlocking.

---

## 5. Combat Resolution

**Status**: DECIDED (current rule + two documented variants; spy rule revised 2026-10-25)

**Implemented in**: `components/game_server/app/engine/combat.py` (ranks in `pieces.py`)

### Current rule (active)

- **Chess piece attacks a stratego piece** (hidden or revealed): the defender is revealed to everyone, then the chess piece wins — **UNLESS the defender is a Bomb**. A Bomb destroys the chess attacker and stays on the board: bombs are only ever defused by Miners, and chess has none. *(The bomb exception was added by the PRP build on 2026-08-20 — the earlier draft of this section said chess "automatically wins" with no exception. Rationale: without it, bombs are dead weight against a chess-heavy attack and the setup mind-game collapses. Confirmed as intended on 2026-10-25. To revert to unconditional chess-wins, delete the bomb branch in `resolve_combat()` and this paragraph.)*
- **Stratego piece attacks a chess piece**: the attacker is revealed to everyone, and the attacker wins — knowing what you are attacking (chess is always visible) is the stratego army's compensation for being individually weaker.
- **Stratego piece attacks another stratego piece**: classic Stratego rank comparison with **1-is-strongest numbering** — the LOWER number wins, equal ranks both die — plus the specialty overrides:
  - **Miner (8) beats Bomb**; every other attacker, the Spy included, dies to a Bomb and the Bomb stays.
  - **Spy (S) takes any piece it attacks** (bar a Bomb), including the Marshal, and **dies to any piece that attacks it**. Spy attacks Spy: the attacker wins. *(Revised 2026-10-25 from the classic "Spy only kills the Marshal" rule — see the documented variant below.)*
  - **The Flag loses to any attacker.**
- **Chess piece attacks another chess piece**: standard chess capture — the moving piece takes the square, no rank comparison.
- **Reveal rule** (closes the old open question): combat reveals BOTH participants' identities to all players, win or lose — nothing is removed silently. A piece that dies *without* combat (swept away by its owner's elimination) is never revealed.

### Documented variant (NOT ACTIVE): classic spy

The Spy only wins when it attacks the Marshal (rank 1); it loses every other fight, attacking or defending. To switch: replace the two spy branches in `combat.py`'s `_stratego_fight()` with a single `spy attacks marshal -> spy wins` check, give the spy a rank number below the scout in `pieces.py`'s `STRATEGO_RANKS` (e.g. 10) so ordinary comparisons go against it, flip these labels, and log the change in `DECISION_LOG.md`.

### Documented variant (NOT ACTIVE): rank-mapping

Every chess piece is assigned a stratego-equivalent rank, and **all** combat (chess-vs-chess, chess-vs-stratego, stratego-vs-stratego) resolves by rank comparison instead of the chess-always-wins rule above:

| Chess piece | Stratego-equivalent rank (1 is strongest) |
|---|---|
| Pawn | ~= 7 (Sergeant) |
| Knight / Bishop | ~= 5 (Captain) |
| Rook | ~= 3 (Colonel) |
| Queen | ~= 1 (Marshal) |
| King | special (exact rule TBD — see the open questions below) |

Open until this variant is activated (decide at activation time, log in `DECISION_LOG.md`):
- Exact numeric rank for King (does it behave like a second Marshal, or something more fragile given it's also a win condition?).
- Whether the Spy-takes-anything and Miner-defuses-Bomb specialties still apply against the mapped chess ranks (e.g., does a Spy attacking a Queen still win?).
An implementation sketch lives in `combat.py`'s module docstring.

To switch the active game to this variant: edit `combat.py`'s resolution function to use the rank-mapping table above instead of the chess-always-wins branch, flip this section's "Current rule" / "Documented variant" labels, and log the change in `DECISION_LOG.md`.

---

## 6. Win Conditions

**Status**: DECIDED (revised 2026-10-25; current rule + three documented variants)

**Implemented in**: `components/game_server/app/engine/win_conditions.py`

### Current rule (active)

The goal is to **capture an enemy's flag AND checkmate their king**. A player is **eliminated** only when they have lost **both**:
- their **flag** (captured by any opponent piece), **and**
- their **king** (captured by any opponent piece — in this game "checkmate" means capture; see section 7).

The two may fall **in either order**, to the same opponent or to different ones. Losing just one changes nothing on its own: a king-less player fights on with the rest of their army until the flag falls, and a flag-less player fights on until the king falls.

The **last player still standing** (not eliminated) wins. An eliminated player's remaining pieces are **removed from the board** (not frozen) — the board thins out as players fall. Pieces removed this way are never revealed (see section 5's reveal rule). If nobody can move, the game is a draw (see section 4).

### Documented variants (NOT ACTIVE)

- **Either-or** (the v1 rule, 2026-08-20 to 2026-10-25): a player is eliminated when they lose EITHER the flag OR the king. Swap: change `all(...)` to `any(...)` in `check_elimination()`.
- **Flag-only**: a player is eliminated only when their flag is captured. Losing the king does not eliminate them — the king simply stops being special and fights on as a slow one-square piece (no substitute rule). Swap: remove `"king"` from `CRITICAL_TYPES` in `win_conditions.py`.
- **King-only**: a player is eliminated only when their king is captured (pure chess-style elimination). The flag then has no game effect at all — it becomes a pure decoy/bluff piece that wastes an opponent's attack when captured. Swap: remove `"flag"` from `CRITICAL_TYPES` in `win_conditions.py`.

To switch the active game to a variant: make the one-line edit above, flip the labels in this section, and log the change in `DECISION_LOG.md`.

---

## 7. Check Rules

**Status**: DECIDED (current rule + one documented variant)

**Implemented in**: `components/game_server/app/engine/movement.py`

### Current rule (active)

**Capturing the king IS checkmate.** There is no check warning and no forced response: the king is captured like any other piece, and that capture satisfies the "checkmate" half of the win condition (see Win Conditions — the flag must fall too). *(Confirmed 2026-10-25 when the flag-AND-king goal was adopted: "checkmate" is read as king capture rather than formal chess check.)*

Rationale: hidden stratego pieces make check unenforceable — you can't reliably warn "your king is threatened" without revealing information about hidden piece identities or positions, which would break the fog-of-war that the stratego half of the game depends on.

### Documented variant (NOT ACTIVE): classic check

Standard chess check/checkmate rules apply to the king: a player must respond to check, and checkmate ends the game immediately for that player (or the whole game, in 2-player mode).

Open until this variant is activated (decide at activation time, log in `DECISION_LOG.md`):
- How checkmate interacts with 3-4 player games (does the checkmated player get eliminated immediately, same as a captured king under the current rule, or does the game pause for the other players?).
- How check detection deals with hidden stratego pieces threatening the king (does a hidden piece "count" as a threat for check purposes, or only revealed/chess pieces?).

To switch the active game to this variant: edit `movement.py`'s move-legality checks to add check/checkmate detection, flip the labels in this section, and log the change in `DECISION_LOG.md`.

---

## 8. Armies

**Status**: DECIDED (v1 defaults locked 2026-08-20; numbering revised 2026-10-25)

**Implemented in**: `components/game_server/app/engine/pieces.py` (labels mirrored in `components/game_client/js/board.js`)

Each player fields **30 pieces**:

- **Chess (16, standard)**: 8 pawns, 2 knights, 2 bishops, 2 rooks, 1 queen, 1 king. Always visible to everyone.
- **Stratego (14, reduced)**, labelled with classic 1-is-strongest numbers: 1 Flag (F), 3 Bombs (B), 1 Spy (S — no number, pure specialty), 1 Marshal (1), 1 General (2), 1 Colonel (3), 1 Major (4), 1 Captain (5), 2 Miners (8), 2 Scouts (9). Hidden until combat reveals them. *(Numbering switched from the modern 10-is-strongest scheme on 2026-10-25 — the numbers in `pieces.py`'s `STRATEGO_RANKS` and the board labels in `game_client/js/board.js` must agree.)*

Why reduced: the full classic 40-piece stratego set plus the chess set is 56 pieces per player, which cannot fit any 3-row setup zone on these boards (the 12x12 two-player zone is 36 squares). 30 pieces fit every zone at every player count.

### Documented variant (NOT ACTIVE): full classic 40-piece stratego set

Viable at 16x16 with a 4-row setup zone (64 squares >= 56 pieces), i.e. as a 2-player-on-a-big-board variant. To activate: replace `STRATEGO_SET_COUNTS` in `pieces.py` with the classic counts (adding the missing rank types — sergeants, lieutenants, etc.), set `SETUP_ZONE_DEPTH = 4` and the board size in `board.py`, flip these labels, and log the change in `DECISION_LOG.md`.

---

## 9. Movement

**Status**: DECIDED (v1 defaults locked by the PRP build, 2026-08-20)

**Implemented in**: `components/game_server/app/engine/movement.py`

- **Chess pieces** move per standard chess, with custom-board simplifications:
  - **No castling, no en passant, no pawn double-step** — free-placement setup means there is no "starting square" for those rules to hang off.
  - **Pawns** move one square "forward" = directly away from their owner's home edge (south's pawns move north, west's pawns move east, etc.); they capture one square diagonally-forward. On reaching the far row/column they **auto-promote to a queen**.
  - Knights jump normally; bishops/rooks/queens slide; the king steps one square any direction (it is an ordinary piece — see section 7).
- **Stratego pieces** move one square orthogonally. Exceptions:
  - **Scout**: slides any distance in a straight orthogonal line (like a rook) and may strike at the end of the run.
  - **Bombs and the Flag**: immobile.
- **Lakes** block occupation and block sliding paths (no scout/rook/bishop/queen may pass through); **knights may leap over lakes**.
- No piece may land on a square occupied by a friendly piece. Landing on an enemy piece is an attack (section 5).

---

## Change process

1. Playtest.
2. Add a row to `DECISION_LOG.md` describing what felt broken.
3. Decide the rule change (promote a documented variant to "current," write a new variant, or tweak a number).
4. Edit this file's relevant section AND the module named in its `Implemented in:` line.
5. Note the module edited in the same `DECISION_LOG.md` row.
