"""Combat resolution when one piece attacks another.

Pure module — no FastAPI imports.

CURRENT RULE (v1):
- chess attacks chess: standard chess capture — the attacker wins.
- chess attacks stratego: the defender is revealed; the chess piece wins
  UNLESS the defender is a bomb — the bomb destroys the attacker and stays
  on the board (bombs are only defused by miners, which chess lacks).
- stratego attacks chess: the attacker is revealed; the attacker wins.
- stratego attacks stratego: classic Stratego — higher rank wins, equal
  ranks both die, miner defuses bomb, spy beats marshal only when the spy
  is the attacker, the flag loses to any attacker.
Combat reveals both participants to everyone (applied by the caller in
state.py), win or lose.

DOCUMENTED VARIANT (NOT ACTIVE): rank-mapping combat. Every chess piece
gets a stratego-equivalent rank (pawn ~4, knight/bishop ~6, rook ~8,
queen ~Marshal, king TBD) and ALL combat resolves by rank comparison.
Sketch: add CHESS_RANK_MAP = {"pawn": 4, "knight": 6, "bishop": 6,
"rook": 8, "queen": 10, "king": <TBD>}, replace the three cross-kind
branches in resolve_combat() with a single _rank_fight() using
rank_of(piece) = STRATEGO_RANKS.get(type) or CHESS_RANK_MAP[type], and
decide whether spy/miner specialties apply to mapped chess ranks (see
RULES.md section 5 stubs). Flip the labels in RULES.md and log the change
in DECISION_LOG.md when activating.
"""

from dataclasses import dataclass

from app.engine.pieces import STRATEGO_RANKS, Piece


@dataclass
class CombatOutcome:
    attacker_survives: bool
    defender_survives: bool
    special: str  # short slug naming the rule branch that decided it


def resolve_combat(attacker: Piece, defender: Piece) -> CombatOutcome:
    """Decide who survives. Never mutates the pieces — state.py applies it."""
    if attacker.kind == "chess" and defender.kind == "chess":
        return CombatOutcome(True, False, "chess_capture")
    if attacker.kind == "chess":  # chess attacks stratego
        if defender.type == "bomb":
            return CombatOutcome(False, True, "bomb_blast")
        return CombatOutcome(True, False, "chess_beats_stratego")
    if defender.kind == "chess":  # stratego attacks chess
        return CombatOutcome(True, False, "stratego_beats_chess")
    return _stratego_fight(attacker, defender)


def _stratego_fight(attacker: Piece, defender: Piece) -> CombatOutcome:
    if defender.type == "bomb":
        if attacker.type == "miner":
            return CombatOutcome(True, False, "miner_defuse")
        return CombatOutcome(False, True, "bomb_blast")
    if defender.type == "flag":
        return CombatOutcome(True, False, "flag_capture")
    if attacker.type == "spy" and defender.type == "marshal":
        return CombatOutcome(True, False, "spy_assassination")
    attacker_rank = STRATEGO_RANKS[attacker.type]
    defender_rank = STRATEGO_RANKS[defender.type]
    if attacker_rank > defender_rank:
        return CombatOutcome(True, False, "rank_win")
    if attacker_rank < defender_rank:
        return CombatOutcome(False, True, "rank_loss")
    return CombatOutcome(False, False, "equal_rank")
