"""Exercise the actual Streamlit app; OCR itself is covered by image-import tests."""

import json
import unittest
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import pandas as pd
from streamlit.testing.v1 import AppTest

from board_app.generators import validate_board
from board_app.image_import import ImageImportResult
from board_app.import_ui import editor_to_board
from board_app.models import DivisorConfig, ImportedBoardConfig
from board_app.presets import PRESETS, divisor_example_board


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def widget(elements, label):
    return next(element for element in elements if element.label == label)


class AppTests(unittest.TestCase):
    def new_app(self, real_exports=False, preset="Divisor-skak"):
        if not real_exports:
            # Layout/bytes have separate exporter tests; keep repeated reruns cheap.
            for name, value in (("board_to_png_bytes", b"test PNG"), ("board_to_pdf_bytes", b"test PDF")):
                mock = patch(f"board_app.exporters.{name}", return_value=value)
                mock.start()
                self.addCleanup(mock.stop)
        app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
        self.assert_clean(app)
        if preset is not None:
            widget(app.selectbox, "Preset").select(preset).run()
            self.assert_clean(app)
        return app

    def assert_clean(self, app):
        self.assertFalse(app.exception, [exception.message for exception in app.exception])

    def payload(self, app):
        return json.loads(app.code[0].value)

    def upload_example(self, app):
        # AppTest does not expose a file-uploader setter. Replace only that boundary.
        uploaded = BytesIO()
        Image.new("RGB", (640, 640), "white").save(uploaded, "PNG")
        uploaded.name = "eksempel.png"
        uploader = patch("board_app.import_ui.st.file_uploader", return_value=uploaded)
        uploader.start()
        self.addCleanup(uploader.stop)
        result = ImageImportResult(divisor_example_board(), [[0.99] * 8 for _ in range(8)], ())
        recognizer = patch("board_app.import_ui.recognize_board_image", return_value=result)
        recognizer.start()
        self.addCleanup(recognizer.stop)
        app.radio(key="board_source").set_value("Importér billede").run()
        self.assert_clean(app)
        widget(app.button, "Aflæs tal fra billedet").click().run()
        self.assert_clean(app)

    def test_default_runs_with_real_exports(self):
        app = self.new_app(real_exports=True, preset=None)
        self.assertEqual(self.payload(app)["board_type"], PRESETS[0].board_type.value)
        self.assertEqual(len(app.get("download_button")), 3)
        self.assertFalse(app.error)
        self.assertEqual(validate_board(app.session_state["current_board"], app.session_state["current_config"]), [])

    def test_every_preset_can_be_selected_and_generated(self):
        app = self.new_app()
        for preset in PRESETS:
            with self.subTest(preset=preset.key):
                widget(app.selectbox, "Preset").select(preset.label).run()
                widget(app.button, "Generer nyt bræt").click().run()
                self.assert_clean(app)
                self.assertFalse(app.error)
                self.assertEqual(self.payload(app)["board_type"], preset.board_type.value)
                self.assertEqual(validate_board(app.session_state["current_board"], app.session_state["current_config"]), [])

    def test_divisor_settings_control_generated_board_and_printed_rule(self):
        app = self.new_app()
        app.number_input(key="divisor_factor").set_value(4)
        app.number_input(key="divisor_min").set_value(10)
        app.number_input(key="divisor_max").set_value(80)
        app.number_input(key="divisor_cells").set_value(17)
        widget(app.button, "Generer nyt bræt").click().run()
        self.assert_clean(app)
        payload = self.payload(app)
        self.assertEqual(payload["config"]["divisible_by"], 4)
        values = sum(payload["board"], [])
        self.assertTrue(all(10 <= value <= 80 for value in values))
        self.assertEqual(sum(value % 4 == 0 for value in values), 17)
        self.assertTrue(any("4 går op i" in element.value for element in app.info))

    def test_example_is_exact_and_preserves_selected_divisor(self):
        app = self.new_app()
        app.number_input(key="divisor_factor").set_value(4)
        widget(app.button, "Generer nyt bræt").click().run()
        widget(app.button, "Brug eksempelbrættet").click().run()
        self.assert_clean(app)
        self.assertEqual(self.payload(app)["board"], divisor_example_board())
        self.assertEqual(app.session_state["current_config"].divisible_by, 4)
        self.assertEqual(app.number_input(key="divisor_cells").value, sum(value % 4 == 0 for row in divisor_example_board() for value in row))
        self.assertFalse(app.error)

    def test_title_theme_and_format_changes_preserve_board(self):
        app = self.new_app()
        board = deepcopy(app.session_state["current_board"])
        app.text_input(key="worksheet_title").set_value("Rikkes præcise talbræt").run()
        widget(app.selectbox, "Farvetema").select("Grøn").run()
        widget(app.selectbox, "Udskriftsformat").select("A3 (liggende)").run()
        app.radio(key="board_source").set_value("Importér billede").run()
        self.assert_clean(app)
        self.assertFalse(app.code)
        app.radio(key="board_source").set_value("Generér talbræt").run()
        self.assert_clean(app)
        payload = self.payload(app)
        self.assertEqual(payload["worksheet_title"], "Rikkes præcise talbræt")
        self.assertEqual(payload["theme"], "Grøn")
        self.assertEqual(payload["page_format"]["key"], "a3")
        self.assertEqual(payload["board"], board)

    def test_generator_settings_remain_consistent_after_visiting_import(self):
        app = self.new_app()
        app.number_input(key="divisor_factor").set_value(4)
        app.number_input(key="divisor_cells").set_value(12)
        widget(app.button, "Generer nyt bræt").click().run()
        board = deepcopy(app.session_state["current_board"])
        app.radio(key="board_source").set_value("Importér billede").run()
        app.radio(key="board_source").set_value("Generér talbræt").run()
        self.assert_clean(app)
        self.assertEqual(app.number_input(key="divisor_factor").value, 4)
        self.assertEqual(app.number_input(key="divisor_cells").value, 12)
        self.assertEqual(app.session_state["current_board"], board)
        self.assertEqual(self.payload(app)["config"]["divisible_by"], 4)

    def test_invalid_configuration_keeps_last_valid_board_without_crashing(self):
        app = self.new_app()
        before = self.payload(app)
        app.number_input(key="divisor_min").set_value(200)
        widget(app.button, "Generer nyt bræt").click().run()
        self.assert_clean(app)
        self.assertTrue(app.error)
        self.assertEqual(self.payload(app)["board"], before["board"])
        self.assertEqual(self.payload(app)["config"], before["config"])
        app.number_input(key="divisor_min").set_value(1)
        widget(app.button, "Generer nyt bræt").click().run()
        self.assert_clean(app)
        self.assertFalse(app.error)

    def test_image_draft_requires_review_and_approved_values_survive_mode_switch(self):
        app = self.new_app()
        self.upload_example(app)
        self.assertFalse(app.code, "Unreviewed OCR must not expose downloadable output.")
        widget(app.button, "Brug talbrættet").click().run()
        self.assert_clean(app)
        self.assertTrue(app.error)
        self.assertIsInstance(app.session_state["current_config"], DivisorConfig)
        widget(app.checkbox, "Jeg har kontrolleret alle 64 tal mod billedet").check()
        widget(app.button, "Brug talbrættet").click().run()
        self.assert_clean(app)
        self.assertIsInstance(app.session_state["current_config"], ImportedBoardConfig)
        self.assertEqual(self.payload(app)["board"], divisor_example_board())
        self.assertEqual(self.payload(app)["config"]["source_name"], "eksempel.png")
        app.radio(key="board_source").set_value("Generér talbræt").run()
        self.assert_clean(app)
        self.assertEqual(self.payload(app)["board_type"], "divisor")
        app.radio(key="board_source").set_value("Importér billede").run()
        self.assert_clean(app)
        self.assertEqual(self.payload(app)["board_type"], "imported")
        self.assertEqual(self.payload(app)["board"], divisor_example_board())

    def test_changing_crop_discards_old_approval(self):
        app = self.new_app()
        self.upload_example(app)
        widget(app.checkbox, "Jeg har kontrolleret alle 64 tal mod billedet").check()
        widget(app.button, "Brug talbrættet").click().run()
        self.assert_clean(app)
        self.assertTrue(app.code)
        widget(app.slider, "Venstre og højre kant (pixels)").set_value((8, 632)).run()
        self.assert_clean(app)
        self.assertFalse(app.code)
        with self.assertRaises(KeyError):
            app.session_state["import_approved"]

    def test_reviewed_corrections_survive_mode_switch_in_editor_and_export(self):
        app = self.new_app()
        self.upload_example(app)
        revision = app.session_state["import_revision"]
        # AppTest exposes the editor's edit delta through its widget state.
        app.session_state[f"import_editor_{revision}"] = {
            "edited_rows": {0: {"A": 77}}, "added_rows": [], "deleted_rows": [],
        }
        widget(app.checkbox, "Jeg har kontrolleret alle 64 tal mod billedet").check()
        widget(app.button, "Brug talbrættet").click().run()
        self.assert_clean(app)
        self.assertEqual(self.payload(app)["board"][0][0], 77)
        self.assertEqual(app.session_state["import_draft"][0][0], 77)
        self.assertEqual(app.dataframe[0].value.iloc[0, 0], 77)
        self.assertGreater(app.session_state["import_revision"], revision)

        app.radio(key="board_source").set_value("Generér talbræt").run()
        app.radio(key="board_source").set_value("Importér billede").run()
        self.assert_clean(app)
        self.assertEqual(app.dataframe[0].value.iloc[0, 0], 77)
        self.assertEqual(self.payload(app)["board"][0][0], 77)
        self.assertTrue(widget(app.checkbox, "Jeg har kontrolleret alle 64 tal mod billedet").value)

        widget(app.button, "Brug talbrættet").click().run()
        self.assert_clean(app)
        self.assertEqual(self.payload(app)["board"][0][0], 77)

    def test_manual_draft_cannot_be_approved_with_empty_cells(self):
        app = self.new_app()
        self.upload_example(app)
        widget(app.button, "Udfyld tallene manuelt").click().run()
        widget(app.checkbox, "Jeg har kontrolleret alle 64 tal mod billedet").check()
        widget(app.button, "Brug talbrættet").click().run()
        self.assert_clean(app)
        self.assertFalse(app.code)
        self.assertTrue(any("A8 mangler et tal" in error.value for error in app.error))


class EditorConversionTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame(divisor_example_board(), index=range(8, 0, -1), columns=list("ABCDEFGH"), dtype="float64")

    def test_numeric_editor_values_become_exact_integers(self):
        self.assertEqual(editor_to_board(self.frame()), divisor_example_board())

    def test_missing_fractional_and_out_of_range_values_are_rejected(self):
        for value in (None, float("nan"), float("inf"), 1.5, 10000, -10000, True, "12"):
            with self.subTest(value=value):
                frame = self.frame().astype(object)
                frame.iloc[0, 0] = value
                with self.assertRaisesRegex(ValueError, "Felt A8"):
                    editor_to_board(frame)

    def test_extra_rows_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "8 rækker og 8 kolonner"):
            editor_to_board(pd.concat([self.frame(), self.frame().iloc[[0]]]))


if __name__ == "__main__":
    unittest.main()
