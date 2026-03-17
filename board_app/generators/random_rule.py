from __future__ import annotations

import random

from board_app.models import BoardMatrix, RandomRuleConfig


def generate_board(config: RandomRuleConfig, rng: random.Random | None = None) -> BoardMatrix:
    rng = rng or random.Random()
    divisible_values = config.divisible_candidates()
    non_divisible_values = config.non_divisible_candidates()

    chosen_values = [rng.choice(divisible_values) for _ in range(config.divisible_cells)]
    chosen_values.extend(
        rng.choice(non_divisible_values)
        for _ in range(config.cell_count - config.divisible_cells)
    )
    rng.shuffle(chosen_values)

    return [
        chosen_values[row_index * config.board_size:(row_index + 1) * config.board_size]
        for row_index in range(config.board_size)
    ]


def validate_board(board: BoardMatrix, config: RandomRuleConfig) -> list[str]:
    issues: list[str] = []
    flat_values = [value for row in board for value in row]

    if len(flat_values) != config.cell_count:
        issues.append("Brættet indeholder ikke præcis 64 felter.")

    out_of_range = [value for value in flat_values if not config.min_value <= value <= config.max_value]
    if out_of_range:
        issues.append("Brættet indeholder tal uden for det tilladte interval.")

    divisible_count = sum(1 for value in flat_values if value % config.divisible_by == 0)
    if divisible_count != config.divisible_cells:
        issues.append(
            f"Brættet har {divisible_count} felter delelige med {config.divisible_by}; forventet er {config.divisible_cells}."
        )

    return issues
