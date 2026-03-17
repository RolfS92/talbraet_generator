from __future__ import annotations

import random

from board_app.knight_utils import generate_knight_path, parse_square
from board_app.models import BOARD_SIZE, BoardMatrix, KnightTableConfig

Square = tuple[int, int]


def generate_board(config: KnightTableConfig, rng: random.Random | None = None) -> BoardMatrix:
    rng = rng or random.Random()
    start = parse_square(config.start_square)
    end = parse_square(config.end_square)
    if start is None or end is None:
        raise ValueError("Knight route requires valid start and end squares.")

    route_squares = generate_knight_path(start, end, config.move_count, rng=rng)
    if route_squares is None:
        raise ValueError("Knight route could not be generated with the requested settings.")

    route_values = config.route_values()
    board = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    for square, value in zip(route_squares, route_values):
        row_index, column_index = square
        board[row_index][column_index] = value

    random_positions = [square for square in _all_squares() if board[square[0]][square[1]] == 0]
    random_values = _random_value_pool(config, len(random_positions), rng)
    for square, value in zip(random_positions, random_values):
        row_index, column_index = square
        board[row_index][column_index] = value

    return board


def validate_board(board: BoardMatrix, config: KnightTableConfig) -> list[str]:
    issues: list[str] = []
    flat_values = [value for row in board for value in row]
    if len(flat_values) != config.cell_count:
        issues.append("Brættet indeholder ikke præcis 64 felter.")
        return issues

    allowed_table_values = set(config.route_values())
    table_positions = {
        (row_index, column_index)
        for row_index, row in enumerate(board)
        for column_index, value in enumerate(row)
        if value in allowed_table_values
    }
    if len(table_positions) != len(config.route_values()):
        issues.append(
            f"Brættet har {len(table_positions)} tabelfelter; forventet er {len(config.route_values())}."
        )

    invalid_random_values = [
        value
        for value in flat_values
        if value not in allowed_table_values and value % config.table_factor == 0
    ]
    if invalid_random_values:
        issues.append("Random-felterne indeholder tal, der stadig passer til tabellen.")

    route_squares = config.route_squares_from_board(board)
    if route_squares is None:
        issues.append("Springerrutens tabeltal forekommer ikke entydigt på brættet.")
        return issues

    start = parse_square(config.start_square)
    end = parse_square(config.end_square)
    if start is None or end is None:
        issues.append("Start- eller slutfelt er ugyldigt.")
        return issues

    if route_squares[0] != start:
        issues.append("Startfeltet indeholder ikke første tabeltal i springerruten.")
    if route_squares[-1] != end:
        issues.append("Slutfeltet indeholder ikke sidste tabeltal i springerruten.")

    if any(not _is_knight_move(first, second) for first, second in zip(route_squares, route_squares[1:])):
        issues.append("Springerrutens tabeltal ligger ikke i gyldige springertræk.")

    return issues


def _all_squares() -> list[Square]:
    return [(row_index, column_index) for row_index in range(BOARD_SIZE) for column_index in range(BOARD_SIZE)]


def _random_value_pool(config: KnightTableConfig, amount: int, rng: random.Random) -> list[int]:
    candidates = config.random_candidates()
    return [rng.choice(candidates) for _ in range(amount)]


def _is_knight_move(first: Square, second: Square) -> bool:
    row_delta = abs(first[0] - second[0])
    column_delta = abs(first[1] - second[1])
    return (row_delta, column_delta) in {(1, 2), (2, 1)}
