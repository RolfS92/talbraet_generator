from __future__ import annotations

from dataclasses import dataclass

from board_app.models import BoardType


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
