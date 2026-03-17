from __future__ import annotations

import random
from functools import lru_cache
from typing import Callable

BOARD_SIZE = 8
FILE_LABELS = tuple("abcdefgh")
KNIGHT_DELTAS = (
    (-2, -1),
    (-2, 1),
    (-1, -2),
    (-1, 2),
    (1, -2),
    (1, 2),
    (2, -1),
    (2, 1),
)
KING_DELTAS = tuple(
    (row_delta, column_delta)
    for row_delta in (-1, 0, 1)
    for column_delta in (-1, 0, 1)
    if (row_delta, column_delta) != (0, 0)
)
Square = tuple[int, int]
NeighborLookup = Callable[[Square, frozenset[Square] | None], tuple[Square, ...]]


def normalize_square_name(value: str) -> str:
    return value.strip().lower()


def parse_square(value: str) -> Square | None:
    square = normalize_square_name(value)
    if len(square) != 2:
        return None

    file_label, rank_label = square[0], square[1]
    if file_label not in FILE_LABELS or rank_label not in "12345678":
        return None

    column_index = FILE_LABELS.index(file_label)
    row_index = BOARD_SIZE - int(rank_label)
    return (row_index, column_index)


def format_square(square: Square) -> str:
    row_index, column_index = square
    return f"{FILE_LABELS[column_index]}{BOARD_SIZE - row_index}"


def squares_have_same_color(first: Square, second: Square) -> bool:
    return ((first[0] + first[1]) % 2) == ((second[0] + second[1]) % 2)


def knight_neighbors(square: Square, allowed_squares: frozenset[Square] | None = None) -> tuple[Square, ...]:
    return _neighbors(square, KNIGHT_DELTAS, allowed_squares)


def king_neighbors(square: Square, allowed_squares: frozenset[Square] | None = None) -> tuple[Square, ...]:
    return _neighbors(square, KING_DELTAS, allowed_squares)


def king_distance(start: Square, end: Square) -> int:
    return max(abs(start[0] - end[0]), abs(start[1] - end[1]))


def _neighbors(
    square: Square,
    deltas: tuple[tuple[int, int], ...],
    allowed_squares: frozenset[Square] | None = None,
) -> tuple[Square, ...]:
    row_index, column_index = square
    neighbors: list[Square] = []

    for row_delta, column_delta in deltas:
        next_row = row_index + row_delta
        next_column = column_index + column_delta
        if not (0 <= next_row < BOARD_SIZE and 0 <= next_column < BOARD_SIZE):
            continue
        next_square = (next_row, next_column)
        if allowed_squares is not None and next_square not in allowed_squares:
            continue
        neighbors.append(next_square)

    return tuple(neighbors)


def find_knight_path(
    start: Square,
    end: Square,
    move_count: int,
    allowed_squares: frozenset[Square] | None = None,
) -> list[Square] | None:
    return _find_path(start, end, move_count, knight_neighbors, allowed_squares)


def find_king_path(
    start: Square,
    end: Square,
    move_count: int,
    allowed_squares: frozenset[Square] | None = None,
) -> list[Square] | None:
    return _find_path(start, end, move_count, king_neighbors, allowed_squares)


def _find_path(
    start: Square,
    end: Square,
    move_count: int,
    neighbor_lookup: NeighborLookup,
    allowed_squares: frozenset[Square] | None = None,
) -> list[Square] | None:
    if move_count < 0:
        return None

    if allowed_squares is not None and (start not in allowed_squares or end not in allowed_squares):
        return None

    can_reach = _build_can_reach(end, allowed_squares, neighbor_lookup)
    if not can_reach(start, move_count):
        return None

    path = [start]
    visited = {start}
    if _search_path(start, end, move_count, neighbor_lookup, allowed_squares, can_reach, visited, path):
        return path
    return None


def generate_knight_path(
    start: Square,
    end: Square,
    move_count: int,
    rng: random.Random | None = None,
    allowed_squares: frozenset[Square] | None = None,
    attempts: int | None = None,
) -> list[Square] | None:
    return _generate_path(start, end, move_count, knight_neighbors, rng, allowed_squares, attempts)


def generate_king_path(
    start: Square,
    end: Square,
    move_count: int,
    rng: random.Random | None = None,
    allowed_squares: frozenset[Square] | None = None,
    attempts: int | None = None,
) -> list[Square] | None:
    return _generate_path(start, end, move_count, king_neighbors, rng, allowed_squares, attempts)


def _generate_path(
    start: Square,
    end: Square,
    move_count: int,
    neighbor_lookup: NeighborLookup,
    rng: random.Random | None = None,
    allowed_squares: frozenset[Square] | None = None,
    attempts: int | None = None,
) -> list[Square] | None:
    if move_count < 0:
        return None

    if allowed_squares is not None and (start not in allowed_squares or end not in allowed_squares):
        return None

    can_reach = _build_can_reach(end, allowed_squares, neighbor_lookup)
    if not can_reach(start, move_count):
        return None

    rng = rng or random.Random()
    successful_paths: list[tuple[int, list[Square]]] = []
    attempt_count = attempts or max(24, min(96, (move_count + 1) * 4))

    for _ in range(attempt_count):
        path = [start]
        visited = {start}
        if _search_path_randomized(
            start,
            end,
            move_count,
            neighbor_lookup,
            allowed_squares,
            can_reach,
            visited,
            path,
            rng,
        ):
            successful_paths.append((_path_spread_score(path), list(path)))

    if successful_paths:
        best_score = max(score for score, _ in successful_paths)
        near_best_paths = [path for score, path in successful_paths if score >= best_score - 120]
        return list(rng.choice(near_best_paths))

    return _find_path(start, end, move_count, neighbor_lookup, allowed_squares)


def _build_can_reach(
    end: Square,
    allowed_squares: frozenset[Square] | None,
    neighbor_lookup: NeighborLookup,
) -> Callable[[Square, int], bool]:
    @lru_cache(maxsize=None)
    def can_reach(square: Square, remaining_moves: int) -> bool:
        if remaining_moves == 0:
            return square == end
        return any(
            can_reach(next_square, remaining_moves - 1)
            for next_square in neighbor_lookup(square, allowed_squares)
        )

    return can_reach


def _search_path(
    current_square: Square,
    end: Square,
    remaining_moves: int,
    neighbor_lookup: NeighborLookup,
    allowed_squares: frozenset[Square] | None,
    can_reach: Callable[[Square, int], bool],
    visited: set[Square],
    path: list[Square],
) -> bool:
    if remaining_moves == 0:
        return current_square == end

    candidates = [
        next_square
        for next_square in neighbor_lookup(current_square, allowed_squares)
        if next_square not in visited and can_reach(next_square, remaining_moves - 1)
    ]
    candidates.sort(
        key=lambda square: (
            square != end if remaining_moves == 1 else 0,
            _reachable_onward_count(
                square,
                remaining_moves - 1,
                neighbor_lookup,
                allowed_squares,
                can_reach,
                visited,
            ),
            _distance_priority(square, end),
            square,
        )
    )

    for next_square in candidates:
        visited.add(next_square)
        path.append(next_square)
        if _search_path(
            next_square,
            end,
            remaining_moves - 1,
            neighbor_lookup,
            allowed_squares,
            can_reach,
            visited,
            path,
        ):
            return True
        path.pop()
        visited.remove(next_square)

    return False


def _search_path_randomized(
    current_square: Square,
    end: Square,
    remaining_moves: int,
    neighbor_lookup: NeighborLookup,
    allowed_squares: frozenset[Square] | None,
    can_reach: Callable[[Square, int], bool],
    visited: set[Square],
    path: list[Square],
    rng: random.Random,
) -> bool:
    if remaining_moves == 0:
        return current_square == end

    candidates = [
        next_square
        for next_square in neighbor_lookup(current_square, allowed_squares)
        if next_square not in visited and can_reach(next_square, remaining_moves - 1)
    ]
    rng.shuffle(candidates)
    candidates.sort(
        key=lambda square: (
            square != end if remaining_moves == 1 else 0,
            _reachable_onward_count(
                square,
                remaining_moves - 1,
                neighbor_lookup,
                allowed_squares,
                can_reach,
                visited,
            ),
            -_spread_candidate_score(path, square),
            _distance_priority(square, end),
        )
    )
    if len(candidates) > 1:
        frontier_size = min(3, len(candidates))
        frontier = list(candidates[:frontier_size])
        rng.shuffle(frontier)
        candidates = frontier + candidates[frontier_size:]

    for next_square in candidates:
        visited.add(next_square)
        path.append(next_square)
        if _search_path_randomized(
            next_square,
            end,
            remaining_moves - 1,
            neighbor_lookup,
            allowed_squares,
            can_reach,
            visited,
            path,
            rng,
        ):
            return True
        path.pop()
        visited.remove(next_square)

    return False


def _reachable_onward_count(
    square: Square,
    remaining_moves_after_arrival: int,
    neighbor_lookup: NeighborLookup,
    allowed_squares: frozenset[Square] | None,
    can_reach: Callable[[Square, int], bool],
    visited: set[Square],
) -> int:
    if remaining_moves_after_arrival <= 0:
        return 0
    return sum(
        1
        for next_square in neighbor_lookup(square, allowed_squares)
        if next_square not in visited and can_reach(next_square, remaining_moves_after_arrival - 1)
    )


def _spread_candidate_score(path: list[Square], candidate: Square) -> int:
    return _path_spread_score([*path, candidate])


def _path_spread_score(path: list[Square]) -> int:
    rows = [square[0] for square in path]
    columns = [square[1] for square in path]
    row_span = (max(rows) - min(rows)) + 1
    column_span = (max(columns) - min(columns)) + 1
    unique_rows = len(set(rows))
    unique_columns = len(set(columns))
    quadrants = len({(square[0] >= BOARD_SIZE // 2, square[1] >= BOARD_SIZE // 2) for square in path})
    edge_touch_count = sum(1 for row_index, column_index in path if row_index in (0, BOARD_SIZE - 1) or column_index in (0, BOARD_SIZE - 1))
    return (
        (row_span * column_span * 100)
        + (unique_rows * 30)
        + (unique_columns * 30)
        + (quadrants * 120)
        + edge_touch_count
    )


def _distance_priority(square: Square, target: Square) -> int:
    return abs(square[0] - target[0]) + abs(square[1] - target[1])
