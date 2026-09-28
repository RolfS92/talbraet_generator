"""Local, cell-by-cell recognition of an upright, cropped 8 × 8 number board.

Recognition produces a draft for human review. A missing cell stays in its
original position; OCR output is never flattened and redistributed across rows.
"""

from __future__ import annotations

import io
import math
import re
import statistics
import threading
import warnings
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from PIL import Image, ImageOps, UnidentifiedImageError

BOARD_SIZE = 8
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MIN_BOARD_SIDE = 80
MIN_CONFIDENCE = 0.65
REVIEW_CONFIDENCE = 0.94
CropBox = tuple[int, int, int, int]
CellReader = Callable[[Image.Image], tuple[str, float] | None]
_OCR_LOCK = threading.Lock()


class ImageImportError(ValueError):
    """An image cannot safely be decoded or used as a board."""


class OCRUnavailableError(RuntimeError):
    """The local OCR engine could not be loaded or run."""


@dataclass(slots=True)
class ImageImportResult:
    values: list[list[int | None]]
    confidence: list[list[float]]
    review_cells: tuple[str, ...]

    @property
    def recognized_count(self) -> int:
        return sum(value is not None for row in self.values for value in row)


def load_board_image(image_bytes: bytes) -> Image.Image:
    """Decode a bounded PNG/JPEG/WebP upload; coordinates use EXIF orientation."""
    if not image_bytes:
        raise ImageImportError("Billedfilen er tom.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ImageImportError("Billedet må højst fylde 10 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(image_bytes)) as source:
                if source.format not in {"PNG", "JPEG", "WEBP"}:
                    raise ImageImportError("Vælg et billede i PNG-, JPG- eller WebP-format.")
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise ImageImportError("Billedet må højst indeholde 20 millioner pixels.")
                if getattr(source, "n_frames", 1) != 1:
                    raise ImageImportError("Vælg et stillbillede uden animation.")
                source.load()
                oriented = ImageOps.exif_transpose(source)
                # Transparent screenshots should look the same as on white paper.
                if "A" in oriented.getbands() or "transparency" in oriented.info:
                    rgba = oriented.convert("RGBA")
                    background = Image.new("RGBA", rgba.size, "white")
                    return Image.alpha_composite(background, rgba).convert("RGB")
                return oriented.convert("RGB")
    except ImageImportError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageImportError("Billedet er for stort til at blive indlæst sikkert.") from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise ImageImportError("Billedet kunne ikke åbnes. Prøv en ny PNG-, JPG- eller WebP-fil.") from exc


def crop_board_image(image: Image.Image, crop: CropBox | None = None) -> Image.Image:
    """Crop exactly the 64 squares, excluding file/rank labels and outer borders."""
    if image.width * image.height > MAX_IMAGE_PIXELS:
        raise ImageImportError("Billedet må højst indeholde 20 millioner pixels.")
    if crop is None:
        crop = (0, 0, image.width, image.height)
    if len(crop) != 4 or any(type(value) is not int for value in crop):
        raise ImageImportError("Beskæringen skal angives som fire hele pixelkoordinater.")
    left, top, right, bottom = crop
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise ImageImportError("Beskæringen skal ligge inden for billedet og have positiv størrelse.")
    width, height = right - left, bottom - top
    if min(width, height) < MIN_BOARD_SIDE:
        raise ImageImportError("Talbrættet skal være mindst 80 pixels bredt og højt.")
    if not 0.65 <= width / height <= 1.55:
        raise ImageImportError("Beskær tæt omkring det kvadratiske talbræt med alle 8 × 8 felter.")
    return image.crop(crop).convert("RGB")


def suggest_board_crop(image: Image.Image) -> CropBox | None:
    """Suggest an axis-aligned grid only when 8 regular rows/columns are visible.

    This is a convenience for screenshots, not a promise to rectify photographs.
    The UI must show the proposed crop and keep its manual controls available.
    """
    if image.width * image.height > MAX_IMAGE_PIXELS:
        return None
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    preview = image.convert("RGB")
    preview.thumbnail((1200, 1200))
    gray = cv2.cvtColor(np.asarray(preview), cv2.COLOR_RGB2GRAY)
    candidates: list[CropBox] = []
    for threshold in (120, 170, 210, 235):
        mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)[1]
        # Separate squares that meet at their corners; restore their edge via
        # center-to-center spacing instead of their eroded rectangle bounds.
        mask = cv2.erode(mask, None, iterations=1)
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            if (10 <= min(width, height) <= min(preview.size) / 6
                    and 0.85 <= width / height <= 1.18
                    and cv2.contourArea(contour) >= width * height * 0.65):
                boxes.append((x + width / 2, y + height / 2, (width + height) / 2))
        if not 28 <= len(boxes) <= 400:
            continue
        remaining = set(range(len(boxes)))
        while remaining:
            component = [remaining.pop()]
            frontier = component.copy()
            while frontier:
                x, y, side = boxes[frontier.pop()]
                for index in tuple(remaining):
                    other_x, other_y, other_side = boxes[index]
                    if (abs(side - other_side) <= max(side, other_side) * 0.15
                            and math.hypot(x - other_x, y - other_y) <= (side + 2) * 2.25):
                        remaining.remove(index)
                        component.append(index)
                        frontier.append(index)
            if not 28 <= len(component) <= 64:
                continue
            points = [boxes[index] for index in component]
            side = statistics.median(point[2] for point in points)

            def axis_centers(axis: int) -> list[float]:
                groups: list[list[float]] = []
                for value in sorted(point[axis] for point in points):
                    if groups and value - statistics.mean(groups[-1]) <= side * 0.2:
                        groups[-1].append(value)
                    else:
                        groups.append([value])
                if len(groups) != 8 or min(map(len, groups)) < 3:
                    return []
                return [statistics.mean(group) for group in groups]

            xs, ys = axis_centers(0), axis_centers(1)
            if not xs or not ys:
                continue
            step_x, step_y = (xs[-1] - xs[0]) / 7, (ys[-1] - ys[0]) / 7
            if not (0.85 <= step_x / step_y <= 1.18 and 0.8 * side <= min(step_x, step_y) <= 1.3 * side):
                continue
            if any(abs(centers[i] - centers[0] - i * step) > step * 0.10
                   for centers, step in ((xs, step_x), (ys, step_y)) for i in range(8)):
                continue
            scale_x, scale_y = image.width / preview.width, image.height / preview.height
            crop = (
                max(0, round((xs[0] - step_x / 2) * scale_x)),
                max(0, round((ys[0] - step_y / 2) * scale_y)),
                min(image.width, round((xs[-1] + step_x / 2) * scale_x)),
                min(image.height, round((ys[-1] + step_y / 2) * scale_y)),
            )
            candidates.append(crop)
    if not candidates:
        return None
    # Multiple complete boards in a screenshot remain a manual choice.
    reference = candidates[0]
    if any(max(abs(a - b) for a, b in zip(reference, crop)) > 5 for crop in candidates[1:]):
        return None
    return reference


@lru_cache(maxsize=1)
def _get_ocr_engine():
    try:
        from rapidocr_onnxruntime import RapidOCR

        # The pinned wheel includes the models: no image or model API requests.
        return RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
    except Exception as exc:
        raise OCRUnavailableError(
            "Billedaflæsningen kunne ikke starte. Du kan stadig skrive tallene manuelt."
        ) from exc


def _read_cell(image: Image.Image) -> tuple[str, float] | None:
    try:
        # RapidOCR changes per-call settings, so shared use must be serialized.
        with _OCR_LOCK:
            result, _ = _get_ocr_engine()(image, use_det=False, use_cls=False, use_rec=True)
        if result is None or len(result) != 1:
            return None
        text, confidence = result[0]
        return str(text), float(confidence)
    except OCRUnavailableError:
        raise
    except Exception as exc:
        raise OCRUnavailableError(
            "Billedaflæsningen blev afbrudt. Prøv igen, eller skriv tallene manuelt."
        ) from exc


def _prepare_cell(cell: Image.Image) -> Image.Image | None:
    """Normalize both light-on-dark and dark-on-light squares before OCR."""
    # Trim grid lines, while preserving digits close to the edge of the square.
    inset = max(1, round(min(cell.size) * 0.025))
    gray = ImageOps.grayscale(cell.crop((inset, inset, cell.width - inset, cell.height - inset)))
    gray.thumbnail((256, 256))
    extrema = gray.getextrema()
    if extrema[1] - extrema[0] < 18:
        return None
    edge = [gray.getpixel((x, 0)) for x in range(gray.width)]
    edge += [gray.getpixel((x, gray.height - 1)) for x in range(gray.width)]
    edge += [gray.getpixel((0, y)) for y in range(gray.height)]
    edge += [gray.getpixel((gray.width - 1, y)) for y in range(gray.height)]
    background = statistics.median(edge)
    gray = ImageOps.autocontrast(gray)
    midpoint = (extrema[0] + extrema[1]) / 2
    if background < midpoint:
        gray = ImageOps.invert(gray)
    # Tighten to the ink so single digits and two-digit values have equal scale.
    ink = gray.point(lambda value: 255 if value < 155 else 0)
    bounds = ink.getbbox()
    if bounds is None:
        return None
    text = gray.crop(bounds)
    scale = 48 / max(1, text.height)
    text = text.resize((max(1, round(text.width * scale)), 48), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (text.width + 24, 64), "white")
    canvas.paste(text, (12, 8))
    return canvas.convert("RGB")


def _numeric_candidate(result: tuple[str, float] | None) -> tuple[int, float] | None:
    if result is None:
        return None
    text, score = result
    text = text.strip().replace("−", "-")
    # Do not turn OCR letters into digits or silently join separate numbers.
    if not re.fullmatch(r"-?[0-9]{1,9}", text):
        return None
    if not math.isfinite(score) or not MIN_CONFIDENCE <= score <= 1:
        return None
    value = int(text)
    if not -9999 <= value <= 9999:
        return None
    return value, score


def recognize_board_image(
    image: Image.Image,
    crop: CropBox | None = None,
    *,
    cell_reader: CellReader | None = None,
) -> ImageImportResult:
    """Read top row as rank 8 and left column as file a, retaining empty cells.

    ``cell_reader`` permits deterministic tests without downloading an OCR engine.
    Users must inspect the draft even when every cell has high OCR confidence.
    """
    board = crop_board_image(image, crop)
    reader = cell_reader or _read_cell
    values: list[list[int | None]] = [[None] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    confidence = [[0.0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    review_cells: list[str] = []
    for row in range(BOARD_SIZE):
        for column in range(BOARD_SIZE):
            cell = board.crop((
                round(column * board.width / BOARD_SIZE),
                round(row * board.height / BOARD_SIZE),
                round((column + 1) * board.width / BOARD_SIZE),
                round((row + 1) * board.height / BOARD_SIZE),
            ))
            prepared = _prepare_cell(cell)
            candidate = _numeric_candidate(reader(prepared)) if prepared is not None else None
            if candidate is not None:
                values[row][column], confidence[row][column] = candidate
            if candidate is None or candidate[1] < REVIEW_CONFIDENCE:
                review_cells.append(f"{'abcdefgh'[column]}{8 - row}")
    return ImageImportResult(values, confidence, tuple(review_cells))
