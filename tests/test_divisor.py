import random
import unittest
from dataclasses import fields

from board_app.generators import generate_board, validate_board
from board_app.generators.divisor import generate_board as generate_divisor_board
from board_app.models import (
    AlternatingRowsConfig,
    BoardType,
    CyclicConfig,
    DivisorConfig,
    HiddenTableConfig,
    ImportedBoardConfig,
    KingTableConfig,
    KnightTableConfig,
    RandomRuleConfig,
)
from board_app.presets import PRESETS, divisor_example_board, divisor_example_config


class DivisorBoardTests(unittest.TestCase):
    def test_generates_exact_requested_divisible_count(self):
        for divisor in (2, 4, 7):
            for count in (0, 1, 32, 63, 64):
                with self.subTest(divisor=divisor, count=count):
                    config = DivisorConfig(divisible_by=divisor, divisible_cells=count)
                    board = generate_divisor_board(config, random.Random(42))
                    self.assertEqual(validate_board(board, config), [])
                    self.assertEqual(len(board), 8)
                    self.assertTrue(all(len(row) == 8 for row in board))
                    self.assertEqual(sum(value % divisor == 0 for row in board for value in row), count)
                    self.assertTrue(all(1 <= value <= 100 for row in board for value in row))

    def test_single_value_intervals(self):
        for config in (
            DivisorConfig(min_value=4, max_value=4, divisible_cells=64),
            DivisorConfig(min_value=3, max_value=3, divisible_cells=0),
            DivisorConfig(divisible_by=1, divisible_cells=64),
        ):
            with self.subTest(config=config):
                self.assertEqual(validate_board(generate_board(config), config), [])

    def test_invalid_settings_are_rejected_before_generation(self):
        invalid_settings = (
            {"divisible_by": 0}, {"divisible_by": -2}, {"divisible_by": True},
            {"divisible_by": 4.5}, {"divisible_by": 10000},
            {"min_value": 0}, {"min_value": -1}, {"min_value": 101},
            {"max_value": 10000}, {"max_value": "100"},
            {"divisible_cells": -1}, {"divisible_cells": 65},
            {"divisible_cells": True}, {"divisible_cells": 2.5},
            {"min_value": 3, "max_value": 3, "divisible_cells": 1},
            {"min_value": 4, "max_value": 4, "divisible_cells": 63},
            {"board_size": 7}, {"board_size": 8.0}, {"board_size": True},
            {"board_size": "8"}, {"board_size": None},
        )
        for settings in invalid_settings:
            with self.subTest(settings=settings):
                config = DivisorConfig(**settings)
                self.assertTrue(config.validate())
                with self.assertRaises(ValueError):
                    generate_board(config)

    def test_example_preserves_orientation_and_is_a_fresh_copy(self):
        board = divisor_example_board()
        self.assertEqual(board[0], [76, 22, 14, 28, 39, 65, 69, 44])
        self.assertEqual(board[-1], [59, 34, 26, 59, 41, 12, 10, 4])
        config = divisor_example_config()
        self.assertEqual(validate_board(board, config), [])
        self.assertIn((0, 0), config.qualifying_squares(board))  # a8 = 76
        self.assertNotIn((0, 4), config.qualifying_squares(board))  # e8 = 39
        self.assertIn((7, 7), config.qualifying_squares(board))  # h1 = 4
        self.assertEqual(len(config.qualifying_squares(board)), config.divisible_cells)
        board[0][0] = 999
        self.assertEqual(divisor_example_board()[0][0], 76)
        four_config = divisor_example_config(4)
        self.assertEqual(validate_board(divisor_example_board(), four_config), [])
        with self.assertRaises(ValueError):
            divisor_example_config(0)

    def test_rule_and_metadata_use_selected_divisor(self):
        config = DivisorConfig(divisible_by=4)
        self.assertIn("4 går op i", config.rule_text())
        self.assertIn("ekstra træk", config.rule_text())
        self.assertEqual(config.to_dict()["board_type"], BoardType.DIVISOR.value)
        self.assertEqual(config.to_dict()["divisible_by"], 4)

    def test_divisor_validation_handles_bad_shape_and_values(self):
        config = DivisorConfig()
        for board in ([[2] * 64], [[2] * 8] * 7, None, [[True] * 8] * 8):
            with self.subTest(board=board):
                self.assertTrue(validate_board(board, config))
        self.assertTrue(validate_board(divisor_example_board(), DivisorConfig(divisible_by=0)))


class ImportedBoardTests(unittest.TestCase):
    def test_exact_board_and_source_metadata_survive_validation(self):
        config = ImportedBoardConfig(source_name="talbræt.png")
        board = divisor_example_board()
        self.assertEqual(validate_board(board, config), [])
        self.assertEqual(config.to_dict()["source_name"], "talbræt.png")
        self.assertEqual(config.to_dict()["board_type"], "imported")
        self.assertEqual(config.label, "Importeret talbræt")

    def test_import_requires_exact_dimensions(self):
        config = ImportedBoardConfig()
        for board in (None, [], [1] * 8, [[1] * 64], [[1] * 8] * 7, [[1] * 7] * 8):
            with self.subTest(board=board):
                self.assertTrue(validate_board(board, config))

    def test_import_rejects_missing_ambiguous_and_out_of_bounds_cells(self):
        config = ImportedBoardConfig()
        for value in (None, "", "12", 12.0, True, False, -10000, 10000, float("nan")):
            with self.subTest(value=value):
                board = divisor_example_board()
                board[0][0] = value
                issues = validate_board(board, config)
                self.assertTrue(issues)
                self.assertIn("a8", issues[0])

    def test_import_accepts_negative_zero_and_boundary_integers(self):
        board = divisor_example_board()
        board[0][:4] = [-9999, -1, 0, 9999]
        self.assertEqual(validate_board(board, ImportedBoardConfig()), [])

    def test_import_cannot_silently_generate_random_replacement(self):
        with self.assertRaisesRegex(ValueError, "Upload et billede"):
            generate_board(ImportedBoardConfig())

    def test_import_rejects_invalid_config_metadata(self):
        for settings in ({"source_name": []}, {"source_name": 123}, {"board_size": 8.0}):
            with self.subTest(settings=settings):
                self.assertTrue(validate_board(divisor_example_board(), ImportedBoardConfig(**settings)))


class ExistingConfigRegressionTests(unittest.TestCase):
    def test_presets_still_generate_valid_boards_and_keep_original_default(self):
        self.assertEqual(PRESETS[0].key, "knight_table")
        config_types = {
            BoardType.CYCLIC: CyclicConfig,
            BoardType.HIDDEN_TABLE: HiddenTableConfig,
            BoardType.KNIGHT_TABLE: KnightTableConfig,
            BoardType.KING_TABLE: KingTableConfig,
            BoardType.DIVISOR: DivisorConfig,
        }
        for preset in PRESETS:
            with self.subTest(preset=preset.key):
                config_type = config_types[preset.board_type]
                config_fields = {field.name for field in fields(config_type) if field.init}
                config = config_type(**{
                    name: value for name, value in preset.defaults.items() if name in config_fields
                })
                self.assertEqual(config.validate(), [])
                self.assertEqual(validate_board(generate_board(config), config), [])

    def test_existing_generators_with_normal_nondefault_settings(self):
        configs = (
            CyclicConfig(sequence_min=2, sequence_max=16, sequence_step=2,
                         table_spacing=3, row_shift=2, random_min=1, random_max=20),
            AlternatingRowsConfig(first_row_start=-7, first_row_end=0,
                                  second_row_start=1, second_row_end=8),
            RandomRuleConfig(min_value=-20, max_value=20, divisible_by=4, divisible_cells=16),
            HiddenTableConfig(table_factor=2, start_square="a8", random_between_count=2),
            KnightTableConfig(table_factor=3, start_square="a1", end_square="b3", move_count=1),
            KingTableConfig(table_factor=2, start_square="a1", end_square="h8", move_count=7),
            KingTableConfig(table_factor=5, route_mode="motif", route_motif="pawn"),
        )
        for config in configs:
            with self.subTest(config=config):
                self.assertEqual(config.validate(), [])
                board = generate_board(config)
                self.assertEqual(validate_board(board, config), [])
                self.assertEqual(len(board), 8)
                self.assertTrue(all(len(row) == 8 for row in board))

    def test_slot_dataclass_validators_call_base_without_super_error(self):
        for config_type in (
            CyclicConfig, AlternatingRowsConfig, RandomRuleConfig,
            HiddenTableConfig, KnightTableConfig, KingTableConfig,
        ):
            with self.subTest(config=config_type.__name__):
                self.assertIsInstance(config_type().validate(), list)
                self.assertTrue(config_type(board_size=7).validate())


if __name__ == "__main__":
    unittest.main()
