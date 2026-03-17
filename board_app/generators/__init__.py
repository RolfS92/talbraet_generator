from __future__ import annotations

from board_app.generators.alternating_rows import (
    generate_board as generate_alternating_rows_board,
)
from board_app.generators.alternating_rows import (
    validate_board as validate_alternating_rows_board,
)
from board_app.generators.cyclic import generate_board as generate_cyclic_board
from board_app.generators.cyclic import validate_board as validate_cyclic_board
from board_app.generators.hidden_table import generate_board as generate_hidden_table_board
from board_app.generators.hidden_table import validate_board as validate_hidden_table_board
from board_app.generators.random_rule import generate_board as generate_random_rule_board
from board_app.generators.random_rule import validate_board as validate_random_rule_board
from board_app.generators.king_table import generate_board as generate_king_table_board
from board_app.generators.king_table import validate_board as validate_king_table_board
from board_app.generators.knight_table import generate_board as generate_knight_table_board
from board_app.generators.knight_table import validate_board as validate_knight_table_board
from board_app.models import (
    AlternatingRowsConfig,
    BoardConfig,
    BoardMatrix,
    CyclicConfig,
    HiddenTableConfig,
    KingTableConfig,
    KnightTableConfig,
    RandomRuleConfig,
)


def generate_board(config: BoardConfig) -> BoardMatrix:
    if isinstance(config, CyclicConfig):
        return generate_cyclic_board(config)
    if isinstance(config, AlternatingRowsConfig):
        return generate_alternating_rows_board(config)
    if isinstance(config, RandomRuleConfig):
        return generate_random_rule_board(config)
    if isinstance(config, HiddenTableConfig):
        return generate_hidden_table_board(config)
    if isinstance(config, KingTableConfig):
        return generate_king_table_board(config)
    if isinstance(config, KnightTableConfig):
        return generate_knight_table_board(config)
    raise TypeError(f"Unsupported config type: {type(config)!r}")


def validate_board(board: BoardMatrix, config: BoardConfig) -> list[str]:
    if isinstance(config, CyclicConfig):
        return validate_cyclic_board(board, config)
    if isinstance(config, AlternatingRowsConfig):
        return validate_alternating_rows_board(board, config)
    if isinstance(config, RandomRuleConfig):
        return validate_random_rule_board(board, config)
    if isinstance(config, HiddenTableConfig):
        return validate_hidden_table_board(board, config)
    if isinstance(config, KingTableConfig):
        return validate_king_table_board(board, config)
    if isinstance(config, KnightTableConfig):
        return validate_knight_table_board(board, config)
    raise TypeError(f"Unsupported config type: {type(config)!r}")
