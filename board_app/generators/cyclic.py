from __future__ import annotations

import random

from board_app.models import BoardMatrix, CyclicConfig


def generate_board(config: CyclicConfig, rng: random.Random | None = None) -> BoardMatrix:
    rng = rng or random.Random()
    pattern = config.expanded_pattern()
    random_candidates = config.random_candidates()
    return [
        [
            _resolved_pattern_value(
                pattern[_pattern_index(config, row_index, column_index)],
                rng,
                random_candidates,
            )
            for column_index in range(config.board_size)
        ]
        for row_index in range(config.board_size)
    ]


def validate_board(board: BoardMatrix, config: CyclicConfig) -> list[str]:
    issues: list[str] = []
    pattern = config.expanded_pattern()
    if not pattern:
        return ["Brættet matcher ikke den forventede cykliske sekvens og forskydning."]

    for row_index, row in enumerate(board):
        for column_index, value in enumerate(row):
            pattern_kind, expected_value = pattern[_pattern_index(config, row_index, column_index)]
            if pattern_kind == "table":
                if value != expected_value:
                    issues.append("Brættet matcher ikke den forventede tabelsekvens.")
                    return issues
                continue

            if not (config.random_min <= value <= config.random_max):
                issues.append("Random-tallene i tabelbrættet ligger uden for det forventede interval.")
                return issues
            if value % config.sequence_step == 0:
                issues.append("Random-tallene i tabelbrættet må ikke passe til tabellen.")
                return issues

    return issues


def _pattern_index(config: CyclicConfig, row_index: int, column_index: int) -> int:
    pattern_length = len(config.expanded_pattern())
    return ((row_index * config.row_shift * config.table_stride()) + column_index) % pattern_length


def _resolved_pattern_value(
    pattern_entry: tuple[str, int | None],
    rng: random.Random,
    random_candidates: list[int],
) -> int:
    pattern_kind, value = pattern_entry
    if pattern_kind == "table" and value is not None:
        return value
    return rng.choice(random_candidates)
