from __future__ import annotations

import json
from io import BytesIO
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

from board_app.branding import FOOTER_TEXT, logo_image
from board_app.models import BoardConfig, BoardMatrix
from board_app.page_formats import DEFAULT_PAGE_FORMAT, EXPORT_DPI, PageFormat
from board_app.rendering import (
    BOARD_AXIS,
    BOTTOM_AXIS_LABELS,
    END_MARKER_FILL,
    END_MARKER_STROKE,
    LEFT_AXIS_LABELS,
    START_MARKER_FILL,
    START_MARKER_STROKE,
    is_dark_square,
)
from board_app.themes import BoardTheme


def _sheet_metrics(page_format: PageFormat) -> dict[str, int]:
    page_width = page_format.width_px
    page_height = page_format.height_px
    return {
        "page_width": page_width,
        "page_height": page_height,
        "page_margin_x": round(page_width * 0.0504),
        "page_margin_top": round(page_height * 0.0496),
        "page_margin_bottom": round(page_height * 0.0435),
        "header_height": round(page_height * 0.1064),
        "footer_height": round(page_height * 0.0254),
        "content_gap": round(page_height * 0.0254),
        "title_font_size": round(page_height * 0.0326),
        "footer_font_size": round(page_height * 0.0169),
        "title_offset_y": round(page_height * 0.0048),
        "logo_max_width": round(page_width * 0.1796),
        "logo_max_height": round(page_height * 0.0822),
    }


def board_to_json(
    config: BoardConfig,
    board: BoardMatrix,
    preset_label: str | None = None,
    worksheet_title: str | None = None,
    theme: BoardTheme | None = None,
    page_format: PageFormat = DEFAULT_PAGE_FORMAT,
) -> str:
    payload = {
        "board_type": config.board_type.value,
        "label": config.label,
        "config": config.to_dict(),
        "coordinates": {
            "columns": list(BOTTOM_AXIS_LABELS),
            "rows": list(LEFT_AXIS_LABELS),
            "bottom_axis": list(BOTTOM_AXIS_LABELS),
            "left_axis": list(LEFT_AXIS_LABELS),
        },
        "board": board,
        "theme": theme.label if theme is not None else "ukendt",
        "page_format": {
            "key": page_format.key,
            "label": page_format.label,
            "width_mm": page_format.width_mm,
            "height_mm": page_format.height_mm,
            "dpi": EXPORT_DPI,
        },
    }
    if preset_label is not None:
        payload["preset"] = preset_label
    if worksheet_title is not None:
        payload["worksheet_title"] = worksheet_title
    return json.dumps(payload, ensure_ascii=False, indent=2)


def board_to_png_bytes(
    board: BoardMatrix,
    worksheet_title: str,
    theme: BoardTheme,
    highlight_squares: Sequence[tuple[int, int]] | None = None,
    route_squares: Sequence[tuple[int, int]] | None = None,
    page_format: PageFormat = DEFAULT_PAGE_FORMAT,
    start_square: tuple[int, int] | None = None,
    end_square: tuple[int, int] | None = None,
) -> bytes:
    image = _compose_sheet_image(
        board,
        worksheet_title,
        theme,
        highlight_squares,
        route_squares,
        page_format,
        start_square,
        end_square,
    )
    buffer = BytesIO()
    image.save(buffer, format="PNG", dpi=(EXPORT_DPI, EXPORT_DPI))
    return buffer.getvalue()


def board_to_pdf_bytes(
    board: BoardMatrix,
    worksheet_title: str,
    theme: BoardTheme,
    highlight_squares: Sequence[tuple[int, int]] | None = None,
    route_squares: Sequence[tuple[int, int]] | None = None,
    page_format: PageFormat = DEFAULT_PAGE_FORMAT,
    start_square: tuple[int, int] | None = None,
    end_square: tuple[int, int] | None = None,
) -> bytes:
    image = _compose_sheet_image(
        board,
        worksheet_title,
        theme,
        highlight_squares,
        route_squares,
        page_format,
        start_square,
        end_square,
    ).convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="PDF", resolution=float(EXPORT_DPI))
    return buffer.getvalue()


def _compose_sheet_image(
    board: BoardMatrix,
    worksheet_title: str,
    theme: BoardTheme,
    highlight_squares: Sequence[tuple[int, int]] | None = None,
    route_squares: Sequence[tuple[int, int]] | None = None,
    page_format: PageFormat = DEFAULT_PAGE_FORMAT,
    start_square: tuple[int, int] | None = None,
    end_square: tuple[int, int] | None = None,
) -> Image.Image:
    metrics = _sheet_metrics(page_format)
    image = Image.new("RGBA", (metrics["page_width"], metrics["page_height"]), "#ffffff")
    draw = ImageDraw.Draw(image)

    title_font = _load_font(metrics["title_font_size"], bold=True, prefer_calibri=True)
    footer_font = _load_font(metrics["footer_font_size"], bold=False, prefer_calibri=True)

    _draw_header(draw, image, worksheet_title, title_font, metrics)
    _draw_board(draw, image, board, theme, highlight_squares, route_squares, metrics, start_square, end_square)
    _draw_footer(draw, footer_font, metrics)

    return image


def _draw_header(
    draw: ImageDraw.ImageDraw,
    image: Image.Image,
    worksheet_title: str,
    title_font: ImageFont.ImageFont,
    metrics: dict[str, int],
) -> None:
    title_position = (metrics["page_margin_x"], metrics["page_margin_top"] + metrics["title_offset_y"])
    draw.text(title_position, worksheet_title, font=title_font, fill="#111111")

    logo = logo_image()
    if logo is None:
        return

    max_width = metrics["logo_max_width"]
    max_height = metrics["logo_max_height"]
    scaled_logo = logo.copy()
    scaled_logo.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    x_position = metrics["page_width"] - metrics["page_margin_x"] - scaled_logo.width
    y_position = metrics["page_margin_top"]
    image.alpha_composite(scaled_logo, (x_position, y_position))


def _draw_board(
    draw: ImageDraw.ImageDraw,
    image: Image.Image,
    board: BoardMatrix,
    theme: BoardTheme,
    highlight_squares: Sequence[tuple[int, int]] | None = None,
    route_squares: Sequence[tuple[int, int]] | None = None,
    metrics: dict[str, int] | None = None,
    start_square: tuple[int, int] | None = None,
    end_square: tuple[int, int] | None = None,
) -> None:
    if metrics is None:
        metrics = _sheet_metrics(DEFAULT_PAGE_FORMAT)
    available_width = metrics["page_width"] - (metrics["page_margin_x"] * 2)
    available_height = (
        metrics["page_height"]
        - metrics["page_margin_top"]
        - metrics["page_margin_bottom"]
        - metrics["header_height"]
        - metrics["footer_height"]
        - metrics["content_gap"]
    )
    axis_band = max(56, min(available_width, available_height) // 18)
    axis_gap = max(18, axis_band // 3)
    board_size = min(available_width - axis_band - axis_gap, available_height - axis_band - axis_gap)
    content_width = axis_band + axis_gap + board_size
    content_height = board_size + axis_gap + axis_band
    content_left = (metrics["page_width"] - content_width) // 2
    content_top = metrics["page_margin_top"] + metrics["header_height"] + max(10, (available_height - content_height) // 2)
    board_left = content_left + axis_band + axis_gap
    board_top = content_top

    outer_rect = (board_left, board_top, board_left + board_size, board_top + board_size)
    outer_line_width = max(5, board_size // 160)
    frame_gap = max(10, board_size // 90)
    inner_line_width = max(2, board_size // 260)
    cell_padding = max(12, board_size // 55)
    outer_radius = max(28, board_size // 20)
    inner_radius = max(22, outer_radius - (frame_gap // 2))

    draw.rounded_rectangle(
        outer_rect,
        radius=outer_radius,
        fill=theme.board_bg,
        outline=theme.frame_outer,
        width=outer_line_width,
    )

    inner_rect = _inset_rect(outer_rect, frame_gap)
    draw.rounded_rectangle(
        inner_rect,
        radius=inner_radius,
        fill=theme.board_bg,
        outline=theme.frame_inner,
        width=inner_line_width,
    )

    cells_rect = _inset_rect(inner_rect, cell_padding)
    sample_cell_bounds = _cell_bounds(cells_rect, 0, 0)
    cell_size = sample_cell_bounds[2] - sample_cell_bounds[0]
    label_font = _load_font(max(24, int(axis_band * 0.55)), bold=True, prefer_calibri=True)

    _draw_board_cells(draw, image, board, theme, cells_rect, cell_size)
    _draw_highlight_overlay(image, cells_rect, theme, highlight_squares)
    _draw_route_overlay(image, cells_rect, theme, route_squares)
    _draw_start_end_markers(image, cells_rect, start_square, end_square)
    _draw_board_axes(
        draw,
        theme,
        cells_rect,
        label_font,
        content_left,
        axis_band,
        board_top + board_size + axis_gap,
    )


def _draw_board_cells(
    draw: ImageDraw.ImageDraw,
    image: Image.Image,
    board: BoardMatrix,
    theme: BoardTheme,
    cells_rect: tuple[int, int, int, int],
    cell_size: int,
) -> None:
    font_cache: dict[int, ImageFont.ImageFont] = {}
    for row_index, row in enumerate(board):
        for column_index, value in enumerate(row):
            bounds = _cell_bounds(cells_rect, row_index, column_index)
            if is_dark_square(row_index, column_index):
                _draw_hatched_cell(image, bounds, theme)
            else:
                draw.rectangle(bounds, fill=theme.light_cell)
            value_text = str(value)
            value_font = _value_font_for_text(value_text, cell_size, font_cache)
            _draw_centered_text(
                draw,
                ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2),
                value_text,
                value_font,
                theme.cell_text,
            )


def _draw_board_axes(
    draw: ImageDraw.ImageDraw,
    theme: BoardTheme,
    cells_rect: tuple[int, int, int, int],
    label_font: ImageFont.ImageFont,
    axis_left: int,
    axis_band: int,
    bottom_axis_top: int,
) -> None:
    axis_center_x = axis_left + (axis_band / 2)
    axis_center_y = bottom_axis_top + (axis_band / 2)

    for row_index, row_label in enumerate(LEFT_AXIS_LABELS):
        row_bounds = _cell_bounds(cells_rect, row_index, 0)
        _draw_centered_text(
            draw,
            (axis_center_x, (row_bounds[1] + row_bounds[3]) / 2),
            str(row_label),
            label_font,
            theme.axis_text,
        )

    for column_index, column_label in enumerate(BOTTOM_AXIS_LABELS):
        column_bounds = _cell_bounds(cells_rect, 0, column_index)
        _draw_centered_text(
            draw,
            ((column_bounds[0] + column_bounds[2]) / 2, axis_center_y),
            column_label,
            label_font,
            theme.axis_text,
        )


def _draw_hatched_cell(image: Image.Image, bounds: tuple[int, int, int, int], theme: BoardTheme) -> None:
    x0, y0, x1, y1 = bounds
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)
    cell_image = Image.new("RGBA", (width, height), theme.dark_cell)
    cell_draw = ImageDraw.Draw(cell_image)
    spacing = max(8, width // 9)
    line_width = max(1, width // 36)

    for offset in range(-height, width, spacing):
        cell_draw.line((offset, height - 1, offset + height, 0), fill=theme.hatch_color, width=line_width)

    image.alpha_composite(cell_image, (x0, y0))


def _value_font_for_text(
    value_text: str,
    cell_size: int,
    font_cache: dict[int, ImageFont.ImageFont],
) -> ImageFont.ImageFont:
    digit_count = len(value_text.lstrip("-"))
    if digit_count <= 1:
        scale = 0.56
    elif digit_count == 2:
        scale = 0.49
    elif digit_count == 3:
        scale = 0.41
    else:
        scale = 0.34

    font_size = max(18, round(cell_size * scale))
    max_width = cell_size * 0.76
    max_height = cell_size * 0.50

    while font_size > 14:
        font = _cached_value_font(font_size, font_cache)
        left, top, right, bottom = font.getbbox(value_text)
        if (right - left) <= max_width and (bottom - top) <= max_height:
            return font
        font_size -= 1

    return _cached_value_font(font_size, font_cache)


def _cached_value_font(
    font_size: int,
    font_cache: dict[int, ImageFont.ImageFont],
) -> ImageFont.ImageFont:
    if font_size not in font_cache:
        font_cache[font_size] = _load_font(font_size, bold=True, prefer_calibri=True)
    return font_cache[font_size]


def _draw_route_overlay(
    image: Image.Image,
    cells_rect: tuple[int, int, int, int],
    theme: BoardTheme,
    route_squares: Sequence[tuple[int, int]] | None,
) -> None:
    if route_squares is None or len(route_squares) < 2:
        return

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    points = [_cell_center(cells_rect, square) for square in route_squares]
    sample_bounds = _cell_bounds(cells_rect, 0, 0)
    cell_width = sample_bounds[2] - sample_bounds[0]
    outer_width = max(8, cell_width // 5)
    inner_width = max(4, cell_width // 10)

    draw.line(points, fill=_hex_to_rgba(theme.frame_inner, 92), width=outer_width)
    draw.line(points, fill=_hex_to_rgba(theme.axis_text, 232), width=inner_width)

    image.alpha_composite(overlay)


def _draw_highlight_overlay(
    image: Image.Image,
    cells_rect: tuple[int, int, int, int],
    theme: BoardTheme,
    highlight_squares: Sequence[tuple[int, int]] | None,
) -> None:
    if not highlight_squares:
        return

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    sample_bounds = _cell_bounds(cells_rect, 0, 0)
    inset = max(5, (sample_bounds[2] - sample_bounds[0]) // 12)
    corner_radius = max(12, (sample_bounds[2] - sample_bounds[0]) // 5)

    for row_index, column_index in highlight_squares:
        bounds = _cell_bounds(cells_rect, row_index, column_index)
        x0, y0, x1, y1 = bounds
        rect = (x0 + inset, y0 + inset, x1 - inset, y1 - inset)
        draw.rounded_rectangle(
            rect,
            radius=corner_radius,
            fill=_hex_to_rgba(theme.axis_text, 34),
            outline=_hex_to_rgba(theme.frame_inner, 230),
            width=max(3, inset // 2),
        )
        draw.rounded_rectangle(
            rect,
            radius=corner_radius,
            outline=(255, 255, 255, 184),
            width=max(1, inset // 4),
        )

    image.alpha_composite(overlay)


def _draw_start_end_markers(
    image: Image.Image,
    cells_rect: tuple[int, int, int, int],
    start_square: tuple[int, int] | None,
    end_square: tuple[int, int] | None,
) -> None:
    if start_square is None and end_square is None:
        return

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    sample_bounds = _cell_bounds(cells_rect, 0, 0)
    cell_width = sample_bounds[2] - sample_bounds[0]
    badge_font = _load_font(max(18, cell_width // 4), bold=True, prefer_calibri=True)

    start_badge_offset = -(cell_width * 0.50)
    end_badge_offset = -(cell_width * 0.50)
    start_radius = cell_width * 0.36
    end_radius = cell_width * 0.36
    if start_square is not None and end_square is not None and start_square == end_square:
        end_badge_offset = cell_width * 0.18
        end_radius = cell_width * 0.25

    if start_square is not None:
        _draw_marker(
            draw,
            _cell_center(cells_rect, start_square),
            "Start",
            START_MARKER_FILL,
            START_MARKER_STROKE,
            badge_font,
            start_badge_offset,
            start_radius,
        )
    if end_square is not None:
        _draw_marker(
            draw,
            _cell_center(cells_rect, end_square),
            "Slut",
            END_MARKER_FILL,
            END_MARKER_STROKE,
            badge_font,
            end_badge_offset,
            end_radius,
        )

    image.alpha_composite(overlay)


def _draw_marker(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    label: str,
    fill_color: str,
    stroke_color: str,
    badge_font: ImageFont.ImageFont,
    badge_offset_y: float,
    ring_radius: float,
) -> None:
    center_x, center_y = center
    outer_radius = ring_radius + max(6, ring_radius * 0.18)
    outer_width = max(6, round(ring_radius * 0.28))
    inner_width = max(4, round(ring_radius * 0.18))

    draw.ellipse(
        (
            center_x - outer_radius,
            center_y - outer_radius,
            center_x + outer_radius,
            center_y + outer_radius,
        ),
        outline=(255, 255, 255, 235),
        width=outer_width,
    )
    draw.ellipse(
        (
            center_x - ring_radius,
            center_y - ring_radius,
            center_x + ring_radius,
            center_y + ring_radius,
        ),
        outline=_hex_to_rgba(stroke_color, 255),
        width=inner_width,
    )

    text_left, text_top, text_right, text_bottom = draw.textbbox((0, 0), label, font=badge_font)
    text_width = text_right - text_left
    text_height = text_bottom - text_top
    badge_width = text_width + max(24, text_height)
    badge_height = max(28, text_height + 8)
    badge_left = center_x - (badge_width / 2)
    badge_top = center_y + badge_offset_y

    draw.rounded_rectangle(
        (
            badge_left,
            badge_top,
            badge_left + badge_width,
            badge_top + badge_height,
        ),
        radius=badge_height / 2,
        fill=_hex_to_rgba(fill_color, 255),
        outline=(255, 255, 255, 255),
        width=max(2, badge_height // 10),
    )
    draw.text(
        (
            center_x - (text_width / 2),
            badge_top + ((badge_height - text_height) / 2) - 1,
        ),
        label,
        font=badge_font,
        fill=(255, 255, 255, 255),
    )


def _cell_bounds(
    rect: tuple[int, int, int, int],
    row_index: int,
    column_index: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = rect
    cell_width = (right - left) / BOARD_AXIS
    cell_height = (bottom - top) / BOARD_AXIS
    x0 = round(left + (column_index * cell_width))
    y0 = round(top + (row_index * cell_height))
    x1 = round(left + ((column_index + 1) * cell_width))
    y1 = round(top + ((row_index + 1) * cell_height))
    return (x0, y0, x1, y1)


def _cell_center(rect: tuple[int, int, int, int], square: tuple[int, int]) -> tuple[int, int]:
    x0, y0, x1, y1 = _cell_bounds(rect, square[0], square[1])
    return (round((x0 + x1) / 2), round((y0 + y1) / 2))


def _inset_rect(rect: tuple[int, int, int, int], amount: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = rect
    return (left + amount, top + amount, right - amount, bottom - amount)


def _draw_footer(
    draw: ImageDraw.ImageDraw,
    footer_font: ImageFont.ImageFont,
    metrics: dict[str, int],
) -> None:
    footer_bbox = draw.textbbox((0, 0), FOOTER_TEXT, font=footer_font)
    footer_height = footer_bbox[3] - footer_bbox[1]
    footer_y = metrics["page_height"] - metrics["page_margin_bottom"] - footer_height
    draw.text((metrics["page_margin_x"], footer_y), FOOTER_TEXT, font=footer_font, fill="#111111")


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    width = right - left
    height = bottom - top
    draw.text((center[0] - (width / 2), center[1] - (height / 2)), text, font=font, fill=fill)


def _load_font(size: int, bold: bool, prefer_calibri: bool) -> ImageFont.ImageFont:
    candidates: list[str] = []
    if prefer_calibri:
        candidates.extend(["calibrib.ttf" if bold else "calibri.ttf", "calibri.ttf"])
    if bold:
        candidates.extend(["arialbd.ttf", "segoeuib.ttf", "segoeui.ttf", "arial.ttf", "tahoma.ttf"])
    else:
        candidates.extend(["segoeui.ttf", "arial.ttf", "tahoma.ttf"])

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex_to_rgba(color: str, alpha: int) -> tuple[int, int, int, int]:
    color = color.lstrip("#")
    if len(color) != 6:
        raise ValueError(f"Expected 6-digit hex color, got {color!r}")
    return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16), alpha)
