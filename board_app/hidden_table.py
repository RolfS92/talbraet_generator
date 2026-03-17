from __future__ import annotations

from board_app.knight_utils import BOARD_SIZE, Square

HIDDEN_TABLE_DIRECTION_RIGHT = "right"
HIDDEN_TABLE_DIRECTION_LEFT = "left"
HIDDEN_TABLE_DIRECTION_DOWN = "down"
HIDDEN_TABLE_DIRECTION_UP = "up"
DEFAULT_HIDDEN_TABLE_DIRECTION = HIDDEN_TABLE_DIRECTION_RIGHT
HIDDEN_TABLE_DIRECTIONS = (
    HIDDEN_TABLE_DIRECTION_RIGHT,
    HIDDEN_TABLE_DIRECTION_LEFT,
    HIDDEN_TABLE_DIRECTION_DOWN,
    HIDDEN_TABLE_DIRECTION_UP,
)

_DIRECTION_LABELS = {
    HIDDEN_TABLE_DIRECTION_RIGHT: "Mod højre",
    HIDDEN_TABLE_DIRECTION_LEFT: "Mod venstre",
    HIDDEN_TABLE_DIRECTION_DOWN: "Nedad",
    HIDDEN_TABLE_DIRECTION_UP: "Opad",
}


def hidden_table_direction_label(direction: str) -> str:
    return _DIRECTION_LABELS.get(direction, direction)


def is_valid_hidden_table_direction(direction: str) -> bool:
    return direction in HIDDEN_TABLE_DIRECTIONS


def hidden_table_traversal(start_square: Square, direction: str) -> list[Square]:
    base_order = _base_order(direction)
    start_index = base_order.index(start_square)
    return [*base_order[start_index:], *base_order[:start_index]]


def _base_order(direction: str) -> list[Square]:
    if direction == HIDDEN_TABLE_DIRECTION_RIGHT:
        return [(row_index, column_index) for row_index in range(BOARD_SIZE) for column_index in range(BOARD_SIZE)]
    if direction == HIDDEN_TABLE_DIRECTION_LEFT:
        return [
            (row_index, column_index)
            for row_index in range(BOARD_SIZE)
            for column_index in range(BOARD_SIZE - 1, -1, -1)
        ]
    if direction == HIDDEN_TABLE_DIRECTION_DOWN:
        return [(row_index, column_index) for column_index in range(BOARD_SIZE) for row_index in range(BOARD_SIZE)]
    if direction == HIDDEN_TABLE_DIRECTION_UP:
        return [
            (row_index, column_index)
            for column_index in range(BOARD_SIZE)
            for row_index in range(BOARD_SIZE - 1, -1, -1)
        ]
    raise ValueError(f"Ukendt retning for skjult tabel: {direction}")
