from __future__ import annotations

import random

from board_app.generators.imported import validate_matrix
from board_app.generators.random_rule import generate_board as generate_random_board
from board_app.generators.random_rule import validate_board as validate_random_board
from board_app.models import BoardMatrix, DivisorConfig


def generate_board(config: DivisorConfig, rng: random.Random | None = None) -> BoardMatrix:
    issues = config.validate()
    if issues:
        raise ValueError(" ".join(issues))
    return generate_random_board(config, rng)


def validate_board(board: BoardMatrix, config: DivisorConfig) -> list[str]:
    issues = config.validate() + validate_matrix(board)
    if issues:
        return issues
    return validate_random_board(board, config)
