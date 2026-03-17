from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoardTheme:
    key: str
    label: str
    board_bg: str
    frame_outer: str
    frame_inner: str
    axis_text: str
    cell_text: str
    light_cell: str
    dark_cell: str
    hatch_color: str


THEMES: tuple[BoardTheme, ...] = (
    BoardTheme(
        key="blue",
        label="Blå",
        board_bg="#fdfbf7",
        frame_outer="#607a86",
        frame_inner="#8da8b3",
        axis_text="#0c5677",
        cell_text="#0c5677",
        light_cell="#fdfbf7",
        dark_cell="#fdfbf7",
        hatch_color="#a9c2ce",
    ),
    BoardTheme(
        key="green",
        label="Grøn",
        board_bg="#f8fbf6",
        frame_outer="#5c7565",
        frame_inner="#91a995",
        axis_text="#24684d",
        cell_text="#24684d",
        light_cell="#f8fbf6",
        dark_cell="#f8fbf6",
        hatch_color="#b7cabd",
    ),
    BoardTheme(
        key="sand",
        label="Sand",
        board_bg="#fff8ee",
        frame_outer="#96754b",
        frame_inner="#c7ac80",
        axis_text="#8b6225",
        cell_text="#8b6225",
        light_cell="#fff8ee",
        dark_cell="#fff8ee",
        hatch_color="#dfccaa",
    ),
)

THEMES_BY_LABEL = {theme.label: theme for theme in THEMES}
DEFAULT_THEME_LABEL = THEMES[0].label
