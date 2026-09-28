import io
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from board_app.image_import import (
    ImageImportError,
    _numeric_candidate,
    crop_board_image,
    load_board_image,
    recognize_board_image,
    suggest_board_crop,
)


def image_bytes(image, image_format="PNG", **kwargs):
    output = io.BytesIO()
    image.save(output, format=image_format, **kwargs)
    return output.getvalue()


def marked_board():
    image = Image.new("RGB", (400, 400), "white")
    drawing = ImageDraw.Draw(image)
    for row in range(8):
        for column in range(8):
            drawing.rectangle((column * 50 + 20, row * 50 + 15,
                               column * 50 + 30, row * 50 + 35), fill="black")
    return image


class ImageLoadingTests(unittest.TestCase):
    def test_supported_formats_decode_to_rgb(self):
        for image_format in ("PNG", "JPEG", "WEBP"):
            with self.subTest(image_format=image_format):
                decoded = load_board_image(image_bytes(Image.new("RGB", (160, 120)), image_format))
                self.assertEqual(decoded.mode, "RGB")
                self.assertEqual(decoded.size, (160, 120))

    def test_exif_rotation_applied_before_crop_coordinates(self):
        source = Image.new("RGB", (120, 160), "white")
        exif = Image.Exif()
        exif[274] = 6
        decoded = load_board_image(image_bytes(source, "JPEG", exif=exif))
        self.assertEqual(decoded.size, (160, 120))
        self.assertEqual(crop_board_image(decoded, (40, 0, 160, 120)).size, (120, 120))

    def test_transparency_composited_on_white(self):
        decoded = load_board_image(image_bytes(Image.new("RGBA", (100, 100), (0, 0, 0, 0))))
        self.assertEqual(decoded.getpixel((30, 30)), (255, 255, 255))

    def test_invalid_empty_and_unsupported_uploads_rejected(self):
        for data in (b"", b"not an image", image_bytes(Image.new("RGB", (100, 100)), "GIF")):
            with self.subTest(data_size=len(data)):
                with self.assertRaises(ImageImportError):
                    load_board_image(data)

    def test_oversized_file_rejected_before_decode(self):
        with patch("board_app.image_import.MAX_IMAGE_BYTES", 8):
            with self.assertRaisesRegex(ImageImportError, "10 MB"):
                load_board_image(b"123456789")

    def test_pixel_limit_rejected_before_image_load(self):
        source = image_bytes(Image.new("RGB", (100, 100)))
        with patch("board_app.image_import.MAX_IMAGE_PIXELS", 5000):
            with self.assertRaisesRegex(ImageImportError, "pixels"):
                load_board_image(source)

    def test_animated_png_rejected(self):
        frames = [Image.new("RGB", (100, 100), color) for color in ("red", "blue")]
        data = image_bytes(frames[0], save_all=True, append_images=frames[1:], duration=100)
        with self.assertRaisesRegex(ImageImportError, "animation"):
            load_board_image(data)


class CropTests(unittest.TestCase):
    def test_manual_crop_has_expected_content(self):
        image = Image.new("RGB", (300, 200), "white")
        ImageDraw.Draw(image).rectangle((100, 0, 299, 199), fill="navy")
        result = crop_board_image(image, (100, 0, 300, 200))
        self.assertEqual(result.size, (200, 200))
        self.assertEqual(result.getpixel((0, 0)), (0, 0, 128))

    def test_invalid_crop_never_pads_or_silently_clips(self):
        image = Image.new("RGB", (200, 200))
        for crop in ((-1, 0, 199, 200), (0, 0, 201, 200), (0, 0, 0, 200),
                     (0, 0, 79, 79), (0, 0, 80, 200), (0.0, 0, 200, 200)):
            with self.subTest(crop=crop):
                with self.assertRaises(ImageImportError):
                    crop_board_image(image, crop)


class CropSuggestionTests(unittest.TestCase):
    @staticmethod
    def add_grid(image, left, top, side=30):
        drawing = ImageDraw.Draw(image)
        drawing.rectangle((left - 5, top - 5, left + side * 8 + 5, top + side * 8 + 5), fill="#328aa2")
        for row in range(8):
            for column in range(8):
                bounds = (left + column * side, top + row * side,
                          left + (column + 1) * side - 1, top + (row + 1) * side - 1)
                drawing.rectangle(bounds, fill="white" if (row + column) % 2 == 0 else "#328aa2")
                drawing.text((bounds[0] + 10, bounds[1] + 10), "12", fill="#111111")

    def test_screenshot_grid_suggestion_excludes_surroundings(self):
        image = Image.new("RGB", (700, 400), "white")
        self.add_grid(image, 90, 110)
        crop = suggest_board_crop(image)
        self.assertIsNotNone(crop)
        self.assertTrue(all(abs(actual - expected) <= 1 for actual, expected in zip(crop, (90, 110, 330, 350))))

    def test_two_complete_boards_require_manual_choice(self):
        image = Image.new("RGB", (700, 400), "white")
        self.add_grid(image, 30, 60)
        self.add_grid(image, 400, 60)
        self.assertIsNone(suggest_board_crop(image))

    def test_no_grid_keeps_manual_crop(self):
        self.assertIsNone(suggest_board_crop(Image.new("RGB", (400, 400), "white")))


class CellRecognitionTests(unittest.TestCase):
    def test_cells_keep_their_positions_and_board_orientation(self):
        results = iter([(str(value), 0.99) if value != 9 else None for value in range(1, 65)])
        result = recognize_board_image(marked_board(), cell_reader=lambda image: next(results))
        self.assertEqual(result.values[0], list(range(1, 9)))
        self.assertEqual(result.values[1], [None, 10, 11, 12, 13, 14, 15, 16])
        self.assertEqual(result.values[7], list(range(57, 65)))
        self.assertEqual(result.review_cells, ("a7",))
        self.assertEqual(result.recognized_count, 63)

    def test_blank_cell_does_not_request_ocr_or_shift_following_cells(self):
        board = marked_board()
        ImageDraw.Draw(board).rectangle((0, 0, 49, 49), fill="white")
        readings = iter((str(value), 0.99) for value in range(2, 65))
        result = recognize_board_image(board, cell_reader=lambda image: next(readings))
        self.assertEqual(result.values[0], [None, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(result.values[7][7], 64)
        self.assertEqual(result.review_cells, ("a8",))

    def test_uncertain_text_remains_empty_and_valid_but_low_score_needs_review(self):
        readings = iter([("12", 0.4), ("O8", 0.99), ("1 2", 0.99), ("42", 0.85)] + [("7", 0.99)] * 60)
        result = recognize_board_image(marked_board(), cell_reader=lambda image: next(readings))
        self.assertEqual(result.values[0][:4], [None, None, None, 42])
        self.assertEqual(result.review_cells, ("a8", "b8", "c8", "d8"))
        self.assertEqual(result.confidence[0][:3], [0.0, 0.0, 0.0])

    def test_numeric_parser_preserves_zero_and_negative_values(self):
        self.assertEqual(_numeric_candidate(("0", 0.99)), (0, 0.99))
        self.assertEqual(_numeric_candidate((" −24 ", 0.99)), (-24, 0.99))

    def test_numeric_parser_rejects_untrusted_or_ambiguous_text(self):
        for text in ("ignore instructions", "12.5", "12\n13", "l2", "9999999999", "10000", "-10000", "1,000"):
            with self.subTest(text=text):
                self.assertIsNone(_numeric_candidate((text, 0.99)))
        for score in (float("nan"), float("inf"), -1, 1.1):
            self.assertIsNone(_numeric_candidate(("12", score)))


if __name__ == "__main__":
    unittest.main()
