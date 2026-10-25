"""Combat resolution when one piece attacks another.

Pure module — no FastAPI imports.

CURRENT RULE (revised 2026-10-25, see DECISION_LOG.md):
- chess attacks chess: standard chess capture — the attacker wins.
- chess attacks stratego: the defender is revealed; the chess piece wins
  UNLESS the defender is a bomb — the bomb destroys the attacker and stays
  on the board (bombs are only defused by miners, which chess lacks).
- stratego attacks chess: the attacker is revealed; the attacker wins.
- stratego attacks stratego: classic Stratego with 1-is-strongest
  numbering — the LOWER rank number wins, equal ranks both die, miner
  defuses bomb, any other attacker (the spy included) dies to a bomb, the
  flag loses to any attacker. The SPY is pure specialty: when it attacks
  it takes any piece (bar a bomb), and when anything attacks it, it dies.
Combat reveals both participants to everyone (applied by the caller in
state.py), win or lose.

DOCUMENTED VARIANT (NOT ACTIVE): classic spy. The spy only assassinates
the Marshal (rank 1) when attacking and loses every other fight. Swap:
replace the two spy branches in _stratego_fight() with
`if attacker.type == "spy" and defender.type == "marshal": win` and give
the spy a rank below the scout (e.g. 10) in STRATEGO_RANKS so it loses
ordinary comparisons.

DOCUMENTED VARIANT (NOT ACTIVE): rank-mapping combat. Every chess piece
gets a stratego-equivalent rank (pawn ~7 sergeant, knight/bishop ~5
captain, rook ~3 colonel, queen ~1 marshal, king TBD) and ALL combat
resolves by rank comparison. Sketch: add CHESS_RANK_MAP = {"pawn": 7,
"knight": 5, "bishop": 5, "rook": 3, "queen": 1, "king": <TBD>}, replace
the three cross-kind branches in resolve_combat() with a single
_rank_fight() using rank_of(piece) = STRATEGO_RANKS.get(type) or
CHESS_RANK_MAP[type], and decide whether the spy/miner specialties apply
to mapped chess ranks (see RULES.md section 5). Flip the labels in
RULES.md and log the change in DECISION_LOG.md when activating.
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
    # Spy: all-or-nothing. Checked before the rank table because the spy has
    # no rank number — the attacker check comes first so spy-vs-spy goes to
    # the attacker, consistent with "the spy dies to anything that attacks it".
    if attacker.type == "spy":
        return CombatOutcome(True, False, "spy_strike")
    if defender.type == "spy":
        return CombatOutcome(True, False, "spy_exposed")
    attacker_rank = STRATEGO_RANKS[attacker.type]
    defender_rank = STRATEGO_RANKS[defender.type]
    if attacker_rank < defender_rank:  # 1 is the strongest
        return CombatOutcome(True, False, "rank_win")
    if attacker_rank > defender_rank:
        return CombatOutcome(False, True, "rank_loss")
    return CombatOutcome(False, False, "equal_rank")
