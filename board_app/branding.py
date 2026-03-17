from __future__ import annotations

import base64
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops

DEFAULT_WORKSHEET_TITLE = "Talbræt 1"
FOOTER_TEXT = "skoleskak.dk"
LOGO_FILENAME = "dss_logo_sort.jpg"


def logo_path() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / LOGO_FILENAME


@lru_cache(maxsize=1)
def logo_data_uri() -> str:
    image = logo_image()
    if image is None:
        return ""

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@lru_cache(maxsize=1)
def logo_image() -> Image.Image | None:
    path = logo_path()
    if not path.exists():
        return None

    image = Image.open(path).convert("RGBA")
    return _trim_logo(image)


def _trim_logo(image: Image.Image) -> Image.Image:
    background = Image.new("RGBA", image.size, image.getpixel((0, 0)))
    difference = ImageChops.difference(image, background)
    bbox = difference.getbbox()
    if bbox is None:
        return image
    return image.crop(bbox)
