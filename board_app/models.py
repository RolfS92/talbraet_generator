from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

from board_app.knight_utils import (
    find_king_path,
    find_knight_path,
    king_distance,
    parse_square,
    squares_have_same_color,
)
from board_app.hidden_table import (
    DEFAULT_HIDDEN_TABLE_DIRECTION,
    hidden_table_traversal,
    is_valid_hidden_table_direction,
)
from board_app.route_motifs import (
    DEFAULT_ROUTE_MOTIF,
    ROUTE_MODE_FREE,
    ROUTE_MODE_MOTIF,
    find_king_motif_route,
    is_valid_motif,
    is_valid_route_mode,
    motif_cell_count,
)

BOARD_SIZE = 8
BOARD_CELLS = BOARD_SIZE * BOARD_SIZE
MAX_BOARD_VALUE = 9999
MAX_KNIGHT_ROUTE_MOVES = 31
MAX_KING_ROUTE_MOVES = 31
BoardMatrix = list[list[int]]


class BoardType(str, Enum):
    CYCLIC = "cyclic"
    ALTERNATING_ROWS = "alternating_rows"
    RANDOM_RULE = "random_rule"
    DIVISOR = "divisor"
    IMPORTED = "imported"
    HIDDEN_TABLE = "hidden_table"
    KNIGHT_TABLE = "knight_table"
    KING_TABLE = "king_table"


@dataclass(slots=True)
class BaseBoardConfig:
    board_type: BoardType = field(init=False)
    label: str = field(init=False)
    board_size: int = BOARD_SIZE

    def validate(self) -> list[str]:
        issues: list[str] = []
        if type(self.board_size) is not int or self.board_size != BOARD_SIZE:
            issues.append("Appen understøtter kun 8x8 boards.")
        return issues

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["board_type"] = self.board_type.value
        return data

    @property
    def cell_count(self) -> int:
        return self.board_size * self.board_size


@dataclass(slots=True)
class CyclicConfig(BaseBoardConfig):
    sequence_min: int = 1
    sequence_max: int = 10
    sequence_step: int = 1
    table_spacing: int = 2
    row_shift: int = 1
    random_min: int = 100
    random_max: int = 999
    board_type: BoardType = field(default=BoardType.CYCLIC, init=False)
    label: str = field(default="Cyklisk sekvens", init=False)

    def validate(self) -> list[str]:
        issues = BaseBoardConfig.validate(self)
        if self.sequence_min > self.sequence_max:
            issues.append("Sekvensens minimum skal være mindre end eller lig maksimum.")
        if self.sequence_step <= 0:
            issues.append("Sekvensens spring skal være større end 0.")
        if self.sequence_step > 0 and (self.sequence_max - self.sequence_min) % self.sequence_step != 0:
            issues.append("Højeste tal skal passe til det valgte tabelspring.")
        if len(self.sequence_values()) < 2:
            issues.append("Den cykliske sekvens skal indeholde mindst to tal.")
        if self.table_spacing < 2:
            issues.append("n mellem tabeltal skal være mindst 2.")
        if self.row_shift == 0:
            issues.append("Rækkeforskydning skal være forskellig fra 0.")
        if self.random_min > self.random_max:
            issues.append("Random-intervallet for tabelbrættet skal have et gyldigt minimum og maksimum.")
        if self.has_random_slots() and not self.random_candidates():
            issues.append("Det valgte tabelspring giver ingen gyldige random-tal mellem tabeltallene.")
        return issues

    def sequence_values(self) -> list[int]:
        if self.sequence_min > self.sequence_max or self.sequence_step <= 0:
            return []
        return list(range(self.sequence_min, self.sequence_max + 1, self.sequence_step))

    def has_random_slots(self) -> bool:
        return self.table_spacing > 2

    def random_slots_between_table_values(self) -> int:
        return max(0, self.table_spacing - 2)

    def table_stride(self) -> int:
        return 1 + self.random_slots_between_table_values()

    def expanded_pattern(self) -> list[tuple[str, int | None]]:
        pattern: list[tuple[str, int | None]] = []
        for value in self.sequence_values():
            pattern.append(("table", value))
            pattern.extend(("random", None) for _ in range(self.random_slots_between_table_values()))
        return pattern

    def random_candidates(self) -> list[int]:
        if self.sequence_step <= 0 or self.random_min > self.random_max:
            return []
        return [
            value
            for value in range(self.random_min, self.random_max + 1)
            if value % self.sequence_step != 0
        ]


@dataclass(slots=True)
class AlternatingRowsConfig(BaseBoardConfig):
    first_row_start: int = 1
    first_row_end: int = 8
    second_row_start: int = 9
    second_row_end: int = 16
    board_type: BoardType = field(default=BoardType.ALTERNATING_ROWS, init=False)
    label: str = field(default="Rækkevis sekvens", init=False)

    def validate(self) -> list[str]:
        issues = BaseBoardConfig.validate(self)
        if self.first_row_start > self.first_row_end:
            issues.append("Første række skal have et gyldigt interval.")
        if self.second_row_start > self.second_row_end:
            issues.append("Anden række skal have et gyldigt interval.")
        if len(self.first_row_values()) != self.board_size:
            issues.append("Første række skal indeholde præcis 8 tal.")
        if len(self.second_row_values()) != self.board_size:
            issues.append("Anden række skal indeholde præcis 8 tal.")
        return issues

    def first_row_values(self) -> list[int]:
        if self.first_row_start > self.first_row_end:
            return []
        return list(range(self.first_row_start, self.first_row_end + 1))

    def second_row_values(self) -> list[int]:
        if self.second_row_start > self.second_row_end:
            return []
        return list(range(self.second_row_start, self.second_row_end + 1))


@dataclass(slots=True)
class RandomRuleConfig(BaseBoardConfig):
    min_value: int = 2
    max_value: int = 100
    divisible_by: int = 4
    divisible_cells: int = BOARD_CELLS // 2
    board_type: BoardType = field(default=BoardType.RANDOM_RULE, init=False)
    label: str = field(default="Tilfældigt board med regler", init=False)

    def validate(self) -> list[str]:
        issues = BaseBoardConfig.validate(self)
        if self.min_value > self.max_value:
            issues.append("Minimum skal være mindre end eller lig maksimum.")
        if self.divisible_by <= 0:
            issues.append("Divisor skal være større end 0.")
        if not 0 <= self.divisible_cells <= self.cell_count:
            issues.append(f"Antal delelige felter skal være mellem 0 og {self.cell_count}.")
        divisible_pool = self.divisible_candidates()
        non_divisible_pool = self.non_divisible_candidates()
        if self.divisible_cells > 0 and not divisible_pool:
            issues.append("Det valgte interval indeholder ingen tal, der opfylder delelighedsreglen.")
        if self.divisible_cells < self.cell_count and not non_divisible_pool:
            issues.append("Det valgte interval indeholder ingen tal, der bryder delelighedsreglen.")
        return issues

    def value_range(self) -> list[int]:
        if self.min_value > self.max_value:
            return []
        return list(range(self.min_value, self.max_value + 1))

    def divisible_candidates(self) -> list[int]:
        if self.divisible_by <= 0:
            return []
        return [value for value in self.value_range() if value % self.divisible_by == 0]

    def non_divisible_candidates(self) -> list[int]:
        if self.divisible_by <= 0:
            return self.value_range()
        return [value for value in self.value_range() if value % self.divisible_by != 0]


@dataclass(slots=True)
class DivisorConfig(RandomRuleConfig):
    min_value: int = 1
    max_value: int = 100
    divisible_by: int = 2
    board_type: BoardType = field(default=BoardType.DIVISOR, init=False)
    label: str = field(default="Divisor-skak", init=False)

    def validate(self) -> list[str]:
        issues = BaseBoardConfig.validate(self)
        for name, value in (
            ("Minimum", self.min_value),
            ("Maksimum", self.max_value),
            ("Divisor", self.divisible_by),
        ):
            if type(value) is not int or not 1 <= value <= MAX_BOARD_VALUE:
                issues.append(f"{name} skal være et helt tal mellem 1 og {MAX_BOARD_VALUE}.")
        if type(self.divisible_cells) is not int:
            issues.append("Antal delelige felter skal være et helt tal.")
        if issues:
            return issues
        return RandomRuleConfig.validate(self)

    def rule_text(self) -> str:
        return (
            f"Hvis din brik lander på et felt med et tal, som {self.divisible_by} går op i, "
            "får du et ekstra træk."
        )

    def qualifying_squares(self, board: BoardMatrix) -> list[tuple[int, int]]:
        if type(self.divisible_by) is not int or self.divisible_by <= 0:
            return []
        return [
            (row_index, column_index)
            for row_index, row in enumerate(board)
            for column_index, value in enumerate(row)
            if type(value) is int and value % self.divisible_by == 0
        ]


@dataclass(slots=True)
class ImportedBoardConfig(BaseBoardConfig):
    source_name: str | None = None
    board_type: BoardType = field(default=BoardType.IMPORTED, init=False)
    label: str = field(default="Importeret talbræt", init=False)

    def validate(self) -> list[str]:
        issues = BaseBoardConfig.validate(self)
        if self.source_name is not None and not isinstance(self.source_name, str):
            issues.append("Billedets filnavn skal være tekst.")
        return issues


@dataclass(slots=True)
class HiddenTableConfig(BaseBoardConfig):
    table_factor: int = 5
    start_square: str = "a8"
    direction: str = DEFAULT_HIDDEN_TABLE_DIRECTION
    random_between_count: int = 4
    board_type: BoardType = field(default=BoardType.HIDDEN_TABLE, init=False)
    label: str = field(default="Find den skjulte tabel", init=False)

    def validate(self) -> list[str]:
        issues = BaseBoardConfig.validate(self)
        if self.table_factor <= 1:
            issues.append("Tabellen skal være mindst 2.")
        start = parse_square(self.start_square)
        if start is None:
            issues.append("Startfelt skal angives som et gyldigt felt som fx a8.")
        if not is_valid_hidden_table_direction(self.direction):
            issues.append("Retning skal være en gyldig retning for den skjulte tabel.")
        if self.random_between_count < 1:
            issues.append("Tilfældige tal mellem tabel skal være mindst 1.")
        if issues:
            return issues
        if self.table_cell_count() < 2:
            issues.append("Der skal være plads til mindst to tabeltal på brættet.")
        return issues

    def table_stride(self) -> int:
        return self.random_between_count + 1

    def traversal_order(self) -> list[tuple[int, int]]:
        start = parse_square(self.start_square)
        if start is None or not is_valid_hidden_table_direction(self.direction):
            return []
        return hidden_table_traversal(start, self.direction)

    def table_squares(self) -> list[tuple[int, int]]:
        order = self.traversal_order()
        return [order[index] for index in range(0, len(order), self.table_stride())]

    def table_cell_count(self) -> int:
        order = self.traversal_order()
        if not order:
            return 0
        return len(range(0, len(order), self.table_stride()))

    def table_values(self) -> list[int]:
        return [self.table_factor * index for index in range(1, self.table_cell_count() + 1)]


@dataclass(slots=True)
class KnightTableConfig(BaseBoardConfig):
    table_factor: int = 7
    start_square: str = "a7"
    end_square: str = "h8"
    move_count: int = 10
    random_min: int = 1
    random_max: int = 100
    board_type: BoardType = field(default=BoardType.KNIGHT_TABLE, init=False)
    label: str = field(default="Springerrute med tabeltal", init=False)

    def validate(self) -> list[str]:
        issues = BaseBoardConfig.validate(self)
        if self.table_factor <= 1:
            issues.append("Tabellen skal være mindst 2, så random-felterne kan være ikke-tabelltal.")
        if self.move_count < 0:
            issues.append("Antal spring skal være 0 eller større.")
        if self.move_count > MAX_KNIGHT_ROUTE_MOVES:
            issues.append(f"Antal spring kan højst være {MAX_KNIGHT_ROUTE_MOVES}.")
        if self.random_min > self.random_max:
            issues.append("Random-intervallet skal have et gyldigt minimum og maksimum.")

        start = parse_square(self.start_square)
        end = parse_square(self.end_square)
        if start is None:
            issues.append("Startfelt skal angives som et gyldigt felt som fx a7.")
        if end is None:
            issues.append("Slutfelt skal angives som et gyldigt felt som fx h8.")

        if self.table_factor > 1 and not self.random_candidates():
            issues.append("Random-intervallet indeholder ingen tal, der ligger uden for den valgte tabel.")

        if start is None or end is None or issues:
            return issues

        same_color = squares_have_same_color(start, end)
        if self.move_count % 2 == 0 and not same_color:
            issues.append("Start- og slutfelt skal have samme farve, når springerruten har et lige antal træk.")
        if self.move_count % 2 == 1 and same_color:
            issues.append("Start- og slutfelt skal have forskellig farve, når springerruten har et ulige antal træk.")

        if issues:
            return issues

        if find_knight_path(start, end, self.move_count) is None:
            issues.append("Der findes ingen springerrute med det valgte antal træk mellem start- og slutfeltet.")
        return issues

    def route_values(self) -> list[int]:
        return [self.table_factor * index for index in range(1, self.move_count + 2)]

    def route_squares(self) -> list[tuple[int, int]] | None:
        start = parse_square(self.start_square)
        end = parse_square(self.end_square)
        if start is None or end is None:
            return None
        return find_knight_path(start, end, self.move_count)

    def route_squares_from_board(self, board: BoardMatrix) -> list[tuple[int, int]] | None:
        return _ordered_route_squares_from_board(board, self.route_values())

    def table_values(self) -> list[int]:
        return self.route_values()

    def random_candidates(self) -> list[int]:
        return _random_candidates_excluding_table(self.table_factor, self.random_min, self.random_max)


@dataclass(slots=True)
class KingTableConfig(BaseBoardConfig):
    table_factor: int = 7
    start_square: str = "a1"
    end_square: str = "h8"
    move_count: int = 10
    route_mode: str = ROUTE_MODE_FREE
    route_motif: str = DEFAULT_ROUTE_MOTIF
    random_min: int = 1
    random_max: int = 100
    board_type: BoardType = field(default=BoardType.KING_TABLE, init=False)
    label: str = field(default="Kongerute med tabeltal", init=False)

    def validate(self) -> list[str]:
        issues = BaseBoardConfig.validate(self)
        if self.table_factor <= 1:
            issues.append("Tabellen skal være mindst 2, så random-felterne kan være ikke-tabelltal.")
        if self.random_min > self.random_max:
            issues.append("Random-intervallet skal have et gyldigt minimum og maksimum.")
        if not is_valid_route_mode(self.route_mode):
            issues.append("Rutetype skal være enten fri rute eller motiv.")
        if self.route_mode == ROUTE_MODE_MOTIF and not is_valid_motif(self.route_motif):
            issues.append("Motivet skal være et gyldigt skakmotiv.")

        if self.table_factor > 1 and not self.random_candidates():
            issues.append("Random-intervallet indeholder ingen tal, der ligger uden for den valgte tabel.")

        if issues:
            return issues

        if self.route_mode == ROUTE_MODE_MOTIF:
            if find_king_motif_route(self.route_motif) is None:
                issues.append("Der findes ingen kongerute for det valgte motiv.")
            return issues

        if self.move_count < 0:
            issues.append("Antal træk skal være 0 eller større.")
        if self.move_count > MAX_KING_ROUTE_MOVES:
            issues.append(f"Antal træk kan højst være {MAX_KING_ROUTE_MOVES}.")

        start = parse_square(self.start_square)
        end = parse_square(self.end_square)
        if start is None:
            issues.append("Startfelt skal angives som et gyldigt felt som fx a1.")
        if end is None:
            issues.append("Slutfelt skal angives som et gyldigt felt som fx h8.")

        if start is None or end is None or issues:
            return issues

        minimum_moves = king_distance(start, end)
        if self.move_count < minimum_moves:
            issues.append(
                f"Start- og slutfelt kræver mindst {minimum_moves} kongetræk med de valgte felter."
            )

        if issues:
            return issues

        if find_king_path(start, end, self.move_count) is None:
            issues.append("Der findes ingen kongerute med det valgte antal træk mellem start- og slutfeltet.")
        return issues

    def route_values(self) -> list[int]:
        return [self.table_factor * index for index in range(1, self.route_length() + 1)]

    def route_squares(self) -> list[tuple[int, int]] | None:
        if self.route_mode == ROUTE_MODE_MOTIF:
            motif_route = find_king_motif_route(self.route_motif)
            if motif_route is None:
                return None
            return list(motif_route)
        start = parse_square(self.start_square)
        end = parse_square(self.end_square)
        if start is None or end is None:
            return None
        return find_king_path(start, end, self.move_count)

    def route_squares_from_board(self, board: BoardMatrix) -> list[tuple[int, int]] | None:
        return _ordered_route_squares_from_board(board, self.route_values())

    def table_values(self) -> list[int]:
        return self.route_values()

    def random_candidates(self) -> list[int]:
        return _random_candidates_excluding_table(self.table_factor, self.random_min, self.random_max)

    def route_length(self) -> int:
        if self.route_mode == ROUTE_MODE_MOTIF:
            return motif_cell_count(self.route_motif)
        return self.move_count + 1


def _ordered_route_squares_from_board(
    board: BoardMatrix,
    route_values: list[int],
) -> list[tuple[int, int]] | None:
    route_value_set = set(route_values)
    positions: dict[int, tuple[int, int]] = {}
    for row_index, row in enumerate(board):
        for column_index, value in enumerate(row):
            if value in route_value_set:
                if value in positions:
                    return None
                positions[value] = (row_index, column_index)

    ordered_squares: list[tuple[int, int]] = []
    for value in route_values:
        square = positions.get(value)
        if square is None:
            return None
        ordered_squares.append(square)
    return ordered_squares


def _random_candidates_excluding_table(table_factor: int, random_min: int, random_max: int) -> list[int]:
    if table_factor <= 1 or random_min > random_max:
        return []
    return [
        value
        for value in range(random_min, random_max + 1)
        if value % table_factor != 0
    ]


BoardConfig = (
    CyclicConfig
    | AlternatingRowsConfig
    | RandomRuleConfig
    | DivisorConfig
    | ImportedBoardConfig
    | HiddenTableConfig
    | KnightTableConfig
    | KingTableConfig
)
