from app.engine.pieces import (
    ARMY_SIZE,
    CHESS_SET_COUNTS,
    STRATEGO_SET_COUNTS,
    STRATEGO_TYPES,
    create_army,
)


def test_army_composition_matches_v1_reduced_set():
    army = create_army("p1")
    assert len(army) == ARMY_SIZE == 30
    counts: dict[str, int] = {}
    for piece in army:
        counts[piece.type] = counts.get(piece.type, 0) + 1
    assert counts == {**CHESS_SET_COUNTS, **STRATEGO_SET_COUNTS}
    assert sum(STRATEGO_SET_COUNTS.values()) == 14


def test_chess_pieces_are_public_stratego_hidden():
    army = create_army("p1")
    for piece in army:
        assert piece.revealed == (piece.kind == "chess")
        assert piece.pos is None
        assert not piece.captured


def test_piece_ids_are_unique_and_opaque():
    armies = create_army("p1") + create_army("p2")
    ids = [piece.id for piece in armies]
    assert len(set(ids)) == len(ids)
    # An id must never encode the piece's identity — that would leak
    # hidden ranks straight through the redacted wire format.
    for piece in armies:
        for type_ in STRATEGO_TYPES:
            assert type_ not in piece.id.lower()
