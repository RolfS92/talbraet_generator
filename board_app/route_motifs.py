from __future__ import annotations

import random
from functools import lru_cache

BOARD_SIZE = 8
ROUTE_MODE_FREE = "free"
ROUTE_MODE_MOTIF = "motif"
ROUTE_MODE_OPTIONS = (ROUTE_MODE_FREE, ROUTE_MODE_MOTIF)
ROUTE_MODE_LABELS = {
    ROUTE_MODE_FREE: "Fri rute",
    ROUTE_MODE_MOTIF: "Motiv",
}
MOTIF_OPTIONS = ("knight", "pawn")
MOTIF_LABELS = {
    "knight": "Springer",
    "pawn": "Bonde",
}
DEFAULT_ROUTE_MOTIF = "knight"
Square = tuple[int, int]

_KING_MOTIF_MASKS: dict[str, tuple[str, ...]] = {
    "pawn": (
        "...XX...",
        "...XX...",
        "..XXXX..",
        "...XX...",
        "...XX...",
        "..XXXX..",
        "..XXXX..",
        "..XXXX..",
    ),
    "knight": (
        "...XXX..",
        "..XXXX..",
        "....XX..",
        "...XXX..",
        "..XXXX..",
        "..XXX...",
        "..XXXX..",
        "..XXXX..",
    ),
}


def route_mode_label(route_mode: str) -> str:
    return ROUTE_MODE_LABELS.get(route_mode, route_mode)


def motif_label(motif: str) -> str:
    return MOTIF_LABELS.get(motif, motif)


def is_valid_route_mode(route_mode: str) -> bool:
    return route_mode in ROUTE_MODE_LABELS


def is_valid_motif(motif: str) -> bool:
    return motif in MOTIF_LABELS


def motif_cell_count(motif: str) -> int:
    return len(king_motif_mask(motif) or ())


def king_motif_mask(motif: str) -> frozenset[Square] | None:
    pattern = _KING_MOTIF_MASKS.get(motif)
    if pattern is None:
        return None
    return frozenset(
        (row_index, column_index)
        for row_index, row in enumerate(pattern)
        for column_index, cell in enumerate(row)
        if cell == "X"
    )


@lru_cache(maxsize=None)
def find_king_motif_route(motif: str) -> tuple[Square, ...] | None:
    row_sequences = _row_sequences_for_motif(motif)
    if not row_sequences:
        return None
    for reverse_rows in (False, True):
        route = _build_row_snake(row_sequences, reverse_rows=reverse_rows, start_from_left=True)
        if route is not None:
            return route
        route = _build_row_snake(row_sequences, reverse_rows=reverse_rows, start_from_left=False)
        if route is not None:
            return route
    return None


def generate_king_motif_route(motif: str, rng: random.Random | None = None) -> list[Square] | None:
    row_sequences = _row_sequences_for_motif(motif)
    if not row_sequences:
        return None

    rng = rng or random.Random()
    attempts = 16
    for _ in range(attempts):
        route = _build_row_snake(
            row_sequences,
            reverse_rows=rng.choice((False, True)),
            start_from_left=rng.choice((False, True)),
            rng=rng,
        )
        if route is not None:
            if rng.choice((False, True)):
                route = tuple(reversed(route))
            return list(route)

    fallback = find_king_motif_route(motif)
    if fallback is None:
        return None
    return list(fallback)


def route_matches_king_motif(motif: str, route_squares: list[Square] | tuple[Square, ...]) -> bool:
    motif_mask = king_motif_mask(motif)
    if motif_mask is None:
        return False
    return tuple(route_squares) and set(route_squares) == set(motif_mask) and len(route_squares) == len(motif_mask)


def _row_sequences_for_motif(motif: str) -> tuple[tuple[Square, ...], ...]:
    motif_mask = king_motif_mask(motif)
    if motif_mask is None:
        return ()

    rows: list[tuple[Square, ...]] = []
    for row_index in range(BOARD_SIZE):
        row_columns = sorted(column_index for current_row, column_index in motif_mask if current_row == row_index)
        if not row_columns:
            continue
        rows.append(tuple((row_index, column_index) for column_index in row_columns))
    return tuple(rows)


def _build_row_snake(
    row_sequences: tuple[tuple[Square, ...], ...],
    *,
    reverse_rows: bool,
    start_from_left: bool,
    rng: random.Random | None = None,
) -> tuple[Square, ...] | None:
    ordered_rows = list(reversed(row_sequences)) if reverse_rows else list(row_sequences)
    path: list[Square] = []
    current_square: Square | None = None
    current_from_left = start_from_left

    for row_sequence in ordered_rows:
        options: list[tuple[Square, ...]] = []
        left_to_right = tuple(row_sequence)
        right_to_left = tuple(reversed(row_sequence))
        preferred = left_to_right if current_from_left else right_to_left
        secondary = right_to_left if current_from_left else left_to_right
        options.extend([preferred, secondary])

        valid_options = []
        for option in options:
            if current_square is None or _is_king_step(current_square, option[0]):
                valid_options.append(option)
        if not valid_options:
            return None

        if rng is not None and len(valid_options) > 1:
            chosen = rng.choice(valid_options)
        else:
            chosen = valid_options[0]

        path.extend(chosen)
        current_square = path[-1]
        current_from_left = chosen[-1][1] <= chosen[0][1]

    if not _is_valid_king_path(path):
        return None
    return tuple(path)


def _is_valid_king_path(path: list[Square]) -> bool:
    return all(_is_king_step(first, second) for first, second in zip(path, path[1:]))


def _is_king_step(first: Square, second: Square) -> bool:
    row_delta = abs(first[0] - second[0])
    column_delta = abs(first[1] - second[1])
    return max(row_delta, column_delta) == 1
