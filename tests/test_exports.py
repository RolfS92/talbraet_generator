import json
import re
import unittest
from io import BytesIO

from PIL import Image, ImageChops

from board_app.exporters import (
    _compose_sheet_image,
    _load_font,
    _sheet_metrics,
    board_to_json,
    board_to_pdf_bytes,
    board_to_png_bytes,
)
from board_app.models import DivisorConfig, ImportedBoardConfig
from board_app.page_formats import EXPORT_DPI, PAGE_FORMATS
from board_app.themes import THEMES


class ExportTests(unittest.TestCase):
    def setUp(self):
        # Values differ across rows and columns to expose accidental transposition.
        self.board = [[row * 8 + column + 1 for column in range(8)] for row in range(8)]
        self.theme = THEMES[0]
        self.config = DivisorConfig()

    def test_png_keeps_print_dimensions_and_resolution(self):
        for page_format in PAGE_FORMATS:
            with self.subTest(page_format=page_format.key):
                data = board_to_png_bytes(
                    self.board, "Divisor-skak", self.theme,
                    page_format=page_format, rule_text=self.config.rule_text(),
                )
                with Image.open(BytesIO(data)) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertEqual(image.size, (page_format.width_px, page_format.height_px))
                    self.assertAlmostEqual(image.info["dpi"][0], EXPORT_DPI, places=1)
                    self.assertAlmostEqual(image.info["dpi"][1], EXPORT_DPI, places=1)
                    image.load()

    def test_rule_is_visible_in_header_without_changing_board_or_logo(self):
        for page_format in PAGE_FORMATS:
            with self.subTest(page_format=page_format.key):
                plain = _compose_sheet_image(self.board, "Divisor-skak", self.theme, page_format=page_format)
                with_rule = _compose_sheet_image(
                    self.board, "Divisor-skak", self.theme,
                    page_format=page_format, rule_text=self.config.rule_text(),
                )
                changed = ImageChops.difference(plain.convert("RGB"), with_rule.convert("RGB")).getbbox()
                self.assertIsNotNone(changed, "The printed rule must be visible.")
                metrics = _sheet_metrics(page_format)
                left, top, right, bottom = changed
                self.assertGreaterEqual(left, metrics["page_margin_x"])
                self.assertGreater(top, metrics["page_margin_top"] + metrics["title_font_size"])
                self.assertLessEqual(bottom, metrics["page_margin_top"] + metrics["header_height"])
                self.assertLess(right, metrics["page_width"] - metrics["page_margin_x"] - metrics["logo_max_width"])

    def test_existing_positional_export_arguments_remain_valid(self):
        data = board_to_png_bytes(
            self.board, "Talbræt", self.theme, [(0, 0)], [(0, 0), (1, 1)], PAGE_FORMATS[0], (0, 0), (1, 1),
        )
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_pdf_is_one_landscape_page_at_correct_print_size(self):
        for page_format in PAGE_FORMATS:
            with self.subTest(page_format=page_format.key):
                data = board_to_pdf_bytes(
                    self.board, "Divisor-skak", self.theme,
                    page_format=page_format, rule_text=self.config.rule_text(),
                )
                self.assertTrue(data.startswith(b"%PDF-"))
                self.assertTrue(data.rstrip().endswith(b"%%EOF"))
                self.assertRegex(data, rb"/Count\s+1\b")
                media_box = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", data)
                self.assertIsNotNone(media_box)
                width, height = map(float, media_box.groups())
                self.assertAlmostEqual(width, page_format.width_mm / 25.4 * 72, delta=0.5)
                self.assertAlmostEqual(height, page_format.height_mm / 25.4 * 72, delta=0.5)

    def test_divisor_json_preserves_rule_parameters_and_orientation(self):
        config = DivisorConfig(divisible_by=4, divisible_cells=16)
        payload = json.loads(board_to_json(config, self.board, worksheet_title="Divisor-skak", theme=self.theme))
        self.assertEqual(payload["board_type"], "divisor")
        self.assertEqual(payload["config"]["divisible_by"], 4)
        self.assertEqual(payload["config"]["divisible_cells"], 16)
        self.assertEqual(payload["board"], self.board)
        self.assertEqual(payload["coordinates"]["rows"], [8, 7, 6, 5, 4, 3, 2, 1])
        self.assertEqual(payload["coordinates"]["columns"], list("abcdefgh"))

    def test_imported_json_preserves_source_and_exact_values(self):
        config = ImportedBoardConfig(source_name="Rikkes talbræt.png")
        payload = json.loads(board_to_json(config, self.board, theme=self.theme, page_format=PAGE_FORMATS[1]))
        self.assertEqual(payload["board_type"], "imported")
        self.assertEqual(payload["config"]["source_name"], "Rikkes talbræt.png")
        self.assertEqual(payload["board"], self.board)
        self.assertEqual(payload["page_format"]["key"], "a3")

    def test_print_font_is_readable_at_requested_size(self):
        # Runs on Linux CI as well as Windows; a tiny bitmap fallback breaks printouts.
        for bold in (False, True):
            with self.subTest(bold=bold):
                font = _load_font(80, bold=bold, prefer_calibri=True)
                left, top, right, bottom = font.getbbox("Divisor-skak ÆØÅ 24")
                self.assertGreater(bottom - top, 45)
                self.assertGreater(right - left, 400)


if __name__ == "__main__":
    unittest.main()
