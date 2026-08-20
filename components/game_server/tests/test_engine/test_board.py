import pytest

from app.engine.board import (
    BOARD_SIZE_BY_PLAYER_COUNT,
    EDGES_BY_PLAYER_COUNT,
    build_board,
    promotion_reached,
)
from app.engine.pieces import ARMY_SIZE


def test_board_size_scales_with_player_count():
    assert BOARD_SIZE_BY_PLAYER_COUNT == {2: 12, 3: 14, 4: 16}
    for count, size in BOARD_SIZE_BY_PLAYER_COUNT.items():
        assert build_board(count).size == size


@pytest.mark.parametrize("count", [2, 3, 4])
def test_every_setup_zone_fits_a_full_army(count):
    board = build_board(count)
    for edge, cells in board.setup_zones.items():
        assert len(cells) >= ARMY_SIZE, f"{edge} zone too small for {count} players"


@pytest.mark.parametrize("count", [2, 3, 4])
def test_setup_zones_are_disjoint_on_board_and_dry(count):
    board = build_board(count)
    seen = set()
    for cells in board.setup_zones.values():
        zone = set(cells)
        assert not zone & seen, "two setup zones overlap"
        seen |= zone
    assert all(board.on_board(pos) for pos in seen)
    assert not seen & board.lake_set, "a setup zone includes a lake square"


@pytest.mark.parametrize("count", [2, 3, 4])
def test_lakes_are_symmetric_around_center(count):
    board = build_board(count)
    lakes = board.lake_set
    for r, c in lakes:
        mirrored = (board.size - 1 - r, board.size - 1 - c)
        assert mirrored in lakes


def test_edge_layouts_per_player_count():
    assert EDGES_BY_PLAYER_COUNT[2] == ["south", "north"]
    assert EDGES_BY_PLAYER_COUNT[3] == ["south", "west", "north"]
    assert EDGES_BY_PLAYER_COUNT[4] == ["south", "west", "north", "east"]
    assert build_board(3).edges == ["south", "west", "north"]


def test_unsupported_player_count_rejected():
    with pytest.raises(ValueError):
        build_board(5)
    with pytest.raises(ValueError):
        build_board(1)


def test_promotion_rows_face_away_from_home_edge():
    assert promotion_reached("south", (0, 4), 12)
    assert not promotion_reached("south", (11, 4), 12)
    assert promotion_reached("north", (11, 4), 12)
    assert promotion_reached("west", (4, 11), 12)
    assert promotion_reached("east", (4, 0), 12)
