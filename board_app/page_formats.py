from __future__ import annotations

from dataclasses import dataclass

EXPORT_DPI = 200
MM_PER_INCH = 25.4


@dataclass(frozen=True, slots=True)
class PageFormat:
    key: str
    label: str
    width_mm: int
    height_mm: int

    @property
    def width_px(self) -> int:
        return round((self.width_mm / MM_PER_INCH) * EXPORT_DPI)

    @property
    def height_px(self) -> int:
        return round((self.height_mm / MM_PER_INCH) * EXPORT_DPI)

    @property
    def aspect_ratio_css(self) -> str:
        return f"{self.width_mm} / {self.height_mm}"


PAGE_FORMATS: tuple[PageFormat, ...] = (
    PageFormat(
        key="a4",
        label="A4 (liggende)",
        width_mm=297,
        height_mm=210,
    ),
    PageFormat(
        key="a3",
        label="A3 (liggende)",
        width_mm=420,
        height_mm=297,
    ),
)

PAGE_FORMATS_BY_LABEL = {page_format.label: page_format for page_format in PAGE_FORMATS}
DEFAULT_PAGE_FORMAT_LABEL = PAGE_FORMATS[0].label
DEFAULT_PAGE_FORMAT = PAGE_FORMATS[0]
