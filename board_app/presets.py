from __future__ import annotations

from dataclasses import dataclass

from board_app.models import MAX_BOARD_VALUE, BoardMatrix, BoardType, DivisorConfig


# Rows run from rank 8 at the top to rank 1 at the bottom, as in the supplied example.
DIVISOR_EXAMPLE_BOARD: tuple[tuple[int, ...], ...] = (
    (76, 22, 14, 28, 39, 65, 69, 44),
    (92, 87, 58, 23, 5, 17, 26, 30),
    (35, 29, 17, 72, 46, 6, 24, 16),
    (12, 38, 9, 31, 57, 84, 39, 42),
    (48, 20, 50, 22, 15, 63, 12, 26),
    (8, 75, 66, 91, 32, 48, 56, 19),
    (13, 28, 41, 70, 96, 21, 60, 53),
    (59, 34, 26, 59, 41, 12, 10, 4),
)


def divisor_example_board() -> BoardMatrix:
    """Return a fresh copy so editing the example never changes the preset."""
    return [list(row) for row in DIVISOR_EXAMPLE_BOARD]


def divisor_example_config(divisible_by: int = 2) -> DivisorConfig:
    config = DivisorConfig(divisible_by=divisible_by, divisible_cells=0)
    if type(divisible_by) is not int or not 1 <= divisible_by <= MAX_BOARD_VALUE:
        raise ValueError(f"Divisor skal være et helt tal mellem 1 og {MAX_BOARD_VALUE}.")
    config.divisible_cells = len(config.qualifying_squares(divisor_example_board()))
    return config


@dataclass(frozen=True, slots=True)
class Preset:
    key: str
    label: str
    board_type: BoardType
    defaults: dict[str, object]
    description: str


PRESETS: tuple[Preset, ...] = (
    Preset(
        key="knight_table",
        label="Springerrute",
        board_type=BoardType.KNIGHT_TABLE,
        defaults={
            "table_factor": 4,
            "start_square": "a7",
            "end_square": "h8",
            "move_count": 10,
            "show_path": True,
        },
        description="Kun springerruten bruger den valgte tabel; alle andre felter er random.",
    ),
    Preset(
        key="king_table",
        label="Kongerute",
        board_type=BoardType.KING_TABLE,
        defaults={
            "table_factor": 4,
            "start_square": "a1",
            "end_square": "h8",
            "move_count": 10,
            "show_path": True,
        },
        description="Kun kongeruten bruger den valgte tabel; alle andre felter er random.",
    ),
    Preset(
        key="motif_table",
        label="Motiv",
        board_type=BoardType.KING_TABLE,
        defaults={
            "table_factor": 4,
            "route_mode": "motif",
            "route_motif": "knight",
            "show_path": True,
        },
        description="Kongeruten følger motivet springer eller bonde; alle andre felter er random.",
    ),
    Preset(
        key="hidden_table",
        label="Find den skjulte tabel",
        board_type=BoardType.HIDDEN_TABLE,
        defaults={
            "table_factor": 4,
            "start_square": "a8",
            "direction": "right",
            "random_between_count": 4,
            "show_table": True,
        },
        description="Tabeltallene gemmes i en valgt retning, og resten af felterne bliver tilfældige tal tæt på tabellen.",
    ),
    Preset(
        key="custom_table",
        label="Tabel",
        board_type=BoardType.CYCLIC,
        defaults={
            "sequence_min": 5,
            "sequence_max": 40,
            "sequence_step": 5,
            "table_spacing": 2,
            "row_shift": 1,
        },
        description="Vælg selv en tabel i sidebaren og opbyg et almindeligt tabelbræt.",
    ),
    Preset(
        key="divisor",
        label="Divisor-skak",
        board_type=BoardType.DIVISOR,
        defaults={
            "min_value": 1,
            "max_value": 100,
            "divisible_by": 2,
            "divisible_cells": 32,
        },
        description="Land på et tal, som den valgte divisor går op i, og få et ekstra træk.",
    ),
)

PRESETS_BY_LABEL = {preset.label: preset for preset in PRESETS}


def preset_table_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for preset in PRESETS:
        if preset.board_type == BoardType.CYCLIC:
            talforloeb = "valgfri tabel" if preset.key == "custom_table" else (
                f"{preset.defaults['sequence_min']}-{preset.defaults['sequence_max']} i spring af {preset.defaults['sequence_step']}"
            )
        elif preset.board_type == BoardType.HIDDEN_TABLE:
            talforloeb = "valgfri tabel skjult i valgt retning + nære random-tal"
        elif preset.board_type == BoardType.DIVISOR:
            talforloeb = "tilfældige tal med et valgt antal delelige felter"
        elif preset.board_type == BoardType.KNIGHT_TABLE:
            talforloeb = "valgfri tabel på ruten + random"
        elif preset.key == "motif_table":
            talforloeb = "valgfri tabel på motiv + random"
        elif preset.board_type == BoardType.KING_TABLE:
            talforloeb = "valgfri tabel på ruten + random"
        else:
            talforloeb = "specialregel"
        rows.append(
            {
                "Preset": preset.label,
                "Type": preset.board_type.value,
                "Talforløb": talforloeb,
                "Standardregel": preset.description,
            }
        )
    return rows
