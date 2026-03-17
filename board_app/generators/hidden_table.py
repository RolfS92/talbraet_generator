from __future__ import annotations

import random

from board_app.models import BoardMatrix, HiddenTableConfig


def generate_board(config: HiddenTableConfig, rng: random.Random | None = None) -> BoardMatrix:
    rng = rng or random.Random()
    board = [[0 for _ in range(config.board_size)] for _ in range(config.board_size)]
    order = config.traversal_order()
    table_values = config.table_values()
    stride = config.table_stride()

    for index, square in enumerate(order):
        row_index, column_index = square
        if index % stride == 0:
            board[row_index][column_index] = table_values[index // stride]
            continue

        previous_table_value = table_values[index // stride]
        next_table_index = (index // stride) + 1
        next_table_value = (
            table_values[next_table_index]
            if next_table_index < len(table_values)
            else previous_table_value + config.table_factor
        )
        board[row_index][column_index] = rng.choice(
            _random_candidates_for_gap(config, previous_table_value, next_table_value)
        )

    return board


def validate_board(board: BoardMatrix, config: HiddenTableConfig) -> list[str]:
    issues: list[str] = []
    order = config.traversal_order()
    table_values = config.table_values()
    stride = config.table_stride()

    if not order or not table_values:
        return ["Brættet matcher ikke den skjulte tabel."]

    for index, square in enumerate(order):
        row_index, column_index = square
        value = board[row_index][column_index]
        if index % stride == 0:
            expected_value = table_values[index // stride]
            if value != expected_value:
                return ["Brættet matcher ikke den skjulte tabel."]
            continue

        previous_table_value = table_values[index // stride]
        next_table_index = (index // stride) + 1
        next_table_value = (
            table_values[next_table_index]
            if next_table_index < len(table_values)
            else previous_table_value + config.table_factor
        )
        if value not in _random_candidates_for_gap(config, previous_table_value, next_table_value):
            return ["De tilfældige tal ligger ikke tæt på den skjulte tabel som forventet."]

    return issues


def _random_candidates_for_gap(
    config: HiddenTableConfig,
    previous_table_value: int,
    next_table_value: int,
) -> list[int]:
    lower_bound = max(1, min(previous_table_value, next_table_value) - config.random_between_count)
    upper_bound = max(previous_table_value, next_table_value) + config.random_between_count
    candidates = [
        value
        for value in range(lower_bound, upper_bound + 1)
        if value % config.table_factor != 0
    ]
    if candidates:
        return candidates

    fallback_upper = max(upper_bound + config.table_factor + config.random_between_count, lower_bound + 1)
    return [
        value
        for value in range(lower_bound, fallback_upper + 1)
        if value % config.table_factor != 0
    ]
