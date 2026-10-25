# Decision Log — ChessStratego Playtests

Running log of rule changes driven by playtesting (primarily with the user's brother). Add one row per session where a rule actually changed. See `RULES.md` for the current state of each rule — this log explains *why* it is what it is.

| Date | What felt broken in play | Rule change made | Code module edited |
|---|---|---|---|
| 2026-08-20 | (v1 build — no play yet) Full 40-piece stratego set + 16 chess = 56 pieces per player cannot fit a 3-row setup zone at any board size under 19x19 | Locked the reduced 14-piece stratego set (1 flag, 3 bombs, 1 spy, 2 scouts, 2 miners, 1 each captain/major/colonel/general/marshal); full classic set documented as an inactive variant | `pieces.py` |
| 2026-08-20 | (v1 build) One fixed board size can't serve 2 and 4 players well | Board scales with player count: 12x12 / 14x14 / 16x16; 2x2 lakes symmetric around center (two blocks at 12, four at 14/16) | `board.py` |
| 2026-08-20 | (v1 build) Adjacent setup zones overlap in board corners at 3-4 players | Pinwheel corner rule: each contested 3x3 corner belongs to exactly one zone (NW->north, NE->east, SE->south, SW->west); every zone keeps >= 33 squares | `board.py` |
| 2026-08-20 | (v1 build) No "standard back rank" exists on a custom per-edge board | Chess placement is fully free inside the setup zone, same as stratego; chess and stratego may mix rows | `state.py` (validation) |
| 2026-08-20 | (v1 build) Setup-order information leak: later players could react to earlier players' visible chess placements | During the setup phase opponents see nothing at all — even chess pieces appear only when play begins | `redaction.py` |
| 2026-08-20 | (v1 build) Turn order was undecided | Round-robin clockwise from creator, one move per turn; eliminated seats skipped; a player with no legal move is auto-skipped; if nobody can move the game is a draw | `movement.py` |
| 2026-08-20 | (v1 build) "Chess always wins" made bombs dead weight against chess-heavy attacks | Bomb exception added: a chess piece attacking a Bomb is destroyed (bombs only fall to Miners); also decided stratego attacker beats any chess defender. NOTE: this supersedes the earlier "chess automatically wins, no exception" draft in RULES.md — revisit in playtest if bombs now feel too strong | `combat.py` |
| 2026-08-20 | (v1 build) Open question: silent removal vs public reveal on combat | Combat reveals BOTH participants to all players, win or lose; pieces removed by owner-elimination are never revealed | `state.py` (reveal application), `redaction.py` |
| 2026-08-20 | (v1 build) Castling / en passant / pawn double-step have no anchor squares under free placement | Dropped all three; pawns auto-promote to queen on the far row; knights may leap lakes, sliders may not | `movement.py` |
| 2026-08-20 | (v1 build) What happens to an eliminated player's army was open | Eliminated player's remaining pieces are removed from the board (not frozen) | `win_conditions.py` |
| 2026-10-25 | (pre-playtest rules review with the user) The v1 build used modern 10-is-strongest Stratego numbering; the user's house set reads 1 as the strongest and 9 as the Scout | Ranks renumbered classic-style: Marshal 1, General 2, Colonel 3, Major 4, Captain 5, Miner 8, Scout 9; lower number wins; Spy has no number (specialty only) | `pieces.py` (ranks), `combat.py` (lower-wins comparison), `game_client/js/board.js` (labels) |
| 2026-10-25 | (pre-playtest rules review) The classic "Spy only kills the Marshal" rule was never the intended one — the Spy is meant to be all-or-nothing | Spy takes ANY piece it attacks (a Bomb still destroys it — only Miners defuse), and dies to ANY piece that attacks it; Spy vs Spy goes to the attacker. Classic spy kept as a documented variant | `combat.py` |
| 2026-10-25 | (pre-playtest rules review) "Lose the flag OR the king" made a game end on a single capture; the intended goal is to take the enemy's flag AND checkmate their king | Elimination now requires BOTH flag and king captured, in either order, by any opponent(s); a player missing one keeps fighting. "Checkmate" means king capture — no formal check, so nothing about hidden pieces leaks. Either-or kept as a documented variant | `win_conditions.py` (RULES.md sections 6 and 7) |

## How to use this log

- One row per playtest session where a rule actually changed (not every session needs a row).
- "What felt broken" is the observation from play — plain language, no rules jargon required.
- "Rule change made" should be specific enough to find in `RULES.md`'s diff.
- "Code module edited" should match the `Implemented in:` line of the `RULES.md` section you changed.
