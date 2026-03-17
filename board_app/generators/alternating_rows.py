from __future__ import annotations

from board_app.models import AlternatingRowsConfig, BoardMatrix


def generate_board(config: AlternatingRowsConfig) -> BoardMatrix:
    first_row = config.first_row_values()
    second_row = config.second_row_values()
    return [
        list(first_row if row_index % 2 == 0 else second_row)
        for row_index in range(config.board_size)
    ]


def validate_board(board: BoardMatrix, config: AlternatingRowsConfig) -> list[str]:
    expected = generate_board(config)
    if board != expected:
        return ["Brættet matcher ikke den forventede skiftevis gentagne rækkesekvens."]
    return []
