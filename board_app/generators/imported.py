from __future__ import annotations

from board_app.models import BOARD_SIZE, MAX_BOARD_VALUE, BoardMatrix, ImportedBoardConfig


def generate_board(config: ImportedBoardConfig) -> BoardMatrix:
    raise ValueError("Upload et billede, og godkend de 64 tal for at oprette et importeret talbræt.")


def validate_matrix(board: BoardMatrix) -> list[str]:
    """Validate the common board shape before rendering or numerical operations."""
    if not isinstance(board, (list, tuple)) or len(board) != BOARD_SIZE:
        return ["Brættet skal indeholde præcis 8 rækker med 8 tal i hver række."]
    if any(not isinstance(row, (list, tuple)) or len(row) != BOARD_SIZE for row in board):
        return ["Brættet skal indeholde præcis 8 rækker med 8 tal i hver række."]

    invalid_squares = [
        f"{chr(ord('a') + column_index)}{BOARD_SIZE - row_index}"
        for row_index, row in enumerate(board)
        for column_index, value in enumerate(row)
        if type(value) is not int or not -MAX_BOARD_VALUE <= value <= MAX_BOARD_VALUE
    ]
    if invalid_squares:
        return [
            f"Alle felter skal indeholde hele tal mellem {-MAX_BOARD_VALUE} og {MAX_BOARD_VALUE}. "
            f"Kontrollér: {', '.join(invalid_squares)}."
        ]
    return []


def validate_board(board: BoardMatrix, config: ImportedBoardConfig) -> list[str]:
    return config.validate() + validate_matrix(board)
