from __future__ import annotations

from html import escape
from typing import Sequence

from board_app.branding import FOOTER_TEXT, logo_data_uri
from board_app.models import BoardMatrix
from board_app.page_formats import DEFAULT_PAGE_FORMAT, PageFormat
from board_app.themes import BoardTheme

COLUMN_LABELS = tuple("abcdefgh")
ROW_LABELS = tuple(range(8, 0, -1))
LEFT_AXIS_LABELS = ROW_LABELS
BOTTOM_AXIS_LABELS = COLUMN_LABELS
BOARD_AXIS = len(BOTTOM_AXIS_LABELS)
START_MARKER_FILL = "#2f9e44"
START_MARKER_STROKE = "#1f6f31"
END_MARKER_FILL = "#e03131"
END_MARKER_STROKE = "#8f1d1d"


def board_to_html(
    board: BoardMatrix,
    title: str,
    theme: BoardTheme,
    highlight_squares: Sequence[tuple[int, int]] | None = None,
    route_squares: Sequence[tuple[int, int]] | None = None,
    start_square: tuple[int, int] | None = None,
    end_square: tuple[int, int] | None = None,
    page_format: PageFormat = DEFAULT_PAGE_FORMAT,
) -> str:
    safe_title = escape(title)
    safe_footer = escape(FOOTER_TEXT)
    logo_src = logo_data_uri()
    logo_html = ""
    if logo_src:
        logo_html = (
            '<img src="{src}" alt="Dansk Skoleskak" '
            'style="max-width:160px; width:22%; min-width:100px; height:auto; object-fit:contain;" />'
        ).format(src=logo_src)

    parts: list[str] = [
        '<div style="display:flex; justify-content:center; width:100%;">',
        (
            '<div style="width:min(100%, 960px); aspect-ratio:{aspect_ratio}; background:#ffffff; padding:20px 28px 18px; '
            'border:1px solid #d7dde5; box-shadow:0 18px 48px rgba(33, 53, 71, 0.15); box-sizing:border-box;">'
        ).format(aspect_ratio=page_format.aspect_ratio_css),
        (
            '<div style="display:grid; grid-template-rows:auto 1fr auto; width:100%; height:100%; '
            'row-gap:14px; min-height:0;">'
        ),
        '<div style="display:flex; align-items:flex-start; justify-content:space-between; gap:16px; min-height:0;">',
        (
            '<div style="font-family:Calibri, Segoe UI, sans-serif; font-size:clamp(20px, 2vw, 30px); '
            'font-weight:700; color:#111111; line-height:1.05; max-width:66%;">{title}</div>'
        ).format(title=safe_title),
        logo_html,
        '</div>',
        '<div style="display:flex; align-items:center; justify-content:center; min-height:0; overflow:hidden; padding:4px 0;">',
        _board_with_axes_html(
            board,
            theme,
            'width:min(100%, 420px);',
            highlight_squares=highlight_squares,
            route_squares=route_squares,
            start_square=start_square,
            end_square=end_square,
            axis_track_size='clamp(18px, 2vw, 28px)',
            layout_gap='clamp(5px, 0.65vw, 10px)',
            label_font_size='clamp(10px, 0.8vw, 16px)',
            value_font_size='clamp(13px, 1.1vw, 21px)',
            value_font_weight=700,
            outer_border_width=4,
            inner_border_width=2,
            outer_padding=7,
            inner_padding=9,
            outer_radius=18,
            inner_radius=14,
        ),
        '</div>',
        (
            '<div style="font-family:Calibri, Segoe UI, sans-serif; font-size:clamp(12px, 0.9vw, 16px); '
            'color:#111111; line-height:1;">{footer}</div>'
        ).format(footer=safe_footer),
        '</div>',
        '</div>',
        '</div>',
    ]
    return "".join(parts)


def board_to_table_html(
    board: BoardMatrix,
    theme: BoardTheme,
    highlight_squares: Sequence[tuple[int, int]] | None = None,
    route_squares: Sequence[tuple[int, int]] | None = None,
    start_square: tuple[int, int] | None = None,
    end_square: tuple[int, int] | None = None,
) -> str:
    parts: list[str] = [
        '<div style="display:flex; justify-content:center; width:100%;">',
        _board_with_axes_html(
            board,
            theme,
            'width:min(100%, 760px);',
            highlight_squares=highlight_squares,
            route_squares=route_squares,
            start_square=start_square,
            end_square=end_square,
            axis_track_size='clamp(24px, 4vw, 40px)',
            layout_gap='clamp(8px, 1vw, 14px)',
            label_font_size='clamp(15px, 1.2vw, 20px)',
            value_font_size='clamp(20px, 2.2vw, 36px)',
            value_font_weight=700,
            outer_border_width=5,
            inner_border_width=2,
            outer_padding=9,
            inner_padding=12,
            outer_radius=22,
            inner_radius=17,
        ),
    ]
    parts.append('</div>')
    return "".join(parts)


def is_dark_square(row_index_from_top: int, column_index: int) -> bool:
    return ((BOARD_AXIS - 1 - row_index_from_top) + column_index) % 2 == 0


def _board_with_axes_html(
    board: BoardMatrix,
    theme: BoardTheme,
    size_css: str,
    highlight_squares: Sequence[tuple[int, int]] | None,
    route_squares: Sequence[tuple[int, int]] | None,
    start_square: tuple[int, int] | None,
    end_square: tuple[int, int] | None,
    axis_track_size: str,
    layout_gap: str,
    label_font_size: str = "clamp(15px, 1.2vw, 20px)",
    value_font_size: str = "clamp(18px, 2vw, 32px)",
    value_font_weight: int = 800,
    outer_border_width: int = 5,
    inner_border_width: int = 2,
    outer_padding: int = 8,
    inner_padding: int = 10,
    outer_radius: int = 22,
    inner_radius: int = 16,
) -> str:
    parts: list[str] = [
        (
            '<div style="{size} display:grid; grid-template-columns:{axis_track} minmax(0, 1fr); '
            'grid-template-rows:minmax(0, 1fr) {axis_track}; column-gap:{gap}; row-gap:{gap}; '
            'align-items:stretch;">'
        ).format(size=size_css, axis_track=axis_track_size, gap=layout_gap),
    ]
    parts.append(_axis_column_html(LEFT_AXIS_LABELS, theme, label_font_size))
    parts.append(
        _board_frame_html(
            board,
            theme,
            highlight_squares,
            route_squares,
            start_square,
            end_square,
            value_font_size,
            value_font_weight,
            outer_border_width,
            inner_border_width,
            outer_padding,
            inner_padding,
            outer_radius,
            inner_radius,
        )
    )
    parts.append('<div></div>')
    parts.append(_axis_row_html(BOTTOM_AXIS_LABELS, theme, label_font_size))
    parts.append('</div>')
    return "".join(parts)


def _axis_column_html(labels: tuple[int, ...], theme: BoardTheme, font_size: str) -> str:
    return (
        '<div style="display:grid; grid-template-rows:repeat({count}, minmax(0, 1fr)); height:100%; width:100%;">{items}</div>'
    ).format(
        count=len(labels),
        items="".join(_axis_label_html(str(label), theme, font_size) for label in labels),
    )


def _axis_row_html(labels: tuple[str, ...], theme: BoardTheme, font_size: str) -> str:
    return (
        '<div style="display:grid; grid-template-columns:repeat({count}, minmax(0, 1fr)); width:100%;">{items}</div>'
    ).format(
        count=len(labels),
        items="".join(_axis_label_html(label, theme, font_size) for label in labels),
    )


def _board_frame_html(
    board: BoardMatrix,
    theme: BoardTheme,
    highlight_squares: Sequence[tuple[int, int]] | None,
    route_squares: Sequence[tuple[int, int]] | None,
    start_square: tuple[int, int] | None,
    end_square: tuple[int, int] | None,
    value_font_size: str,
    value_font_weight: int,
    outer_border_width: int,
    inner_border_width: int,
    outer_padding: int,
    inner_padding: int,
    outer_radius: int,
    inner_radius: int,
) -> str:
    cell_radius = max(8, inner_radius - 6)
    return (
        '<div style="width:100%; aspect-ratio:1 / 1; background:{board_bg}; '
        'border:{outer_border_width}px solid {frame_outer}; border-radius:{outer_radius}px; '
        'padding:{outer_padding}px; box-sizing:border-box;">'
        '<div style="width:100%; height:100%; background:{board_bg}; '
        'border:{inner_border_width}px solid {frame_inner}; border-radius:{inner_radius}px; '
        'padding:{inner_padding}px; box-sizing:border-box;">'
        '<div style="position:relative; width:100%; height:100%; overflow:hidden; border-radius:{cell_radius}px;">'
        '<div style="display:grid; width:100%; height:100%; grid-template-columns:repeat({board_axis}, minmax(0, 1fr)); '
        'grid-template-rows:repeat({board_axis}, minmax(0, 1fr));">{cells}</div>'
        '{highlight_overlay}'
        '{route_overlay}'
        '{marker_overlay}'
        '</div>'
        '</div>'
        '</div>'
    ).format(
        board_bg=theme.board_bg,
        outer_border_width=outer_border_width,
        frame_outer=theme.frame_outer,
        outer_radius=outer_radius,
        outer_padding=outer_padding,
        inner_border_width=inner_border_width,
        frame_inner=theme.frame_inner,
        inner_radius=inner_radius,
        inner_padding=inner_padding,
        board_axis=BOARD_AXIS,
        cell_radius=cell_radius,
        cells=_cell_grid_html(board, theme, value_font_size, value_font_weight),
        highlight_overlay=_highlight_overlay_html(highlight_squares, theme),
        route_overlay=_route_overlay_html(route_squares, theme),
        marker_overlay=_marker_overlay_html(start_square, end_square),
    )


def _cell_grid_html(
    board: BoardMatrix,
    theme: BoardTheme,
    font_size: str,
    font_weight: int,
) -> str:
    parts: list[str] = []
    for row_index, row in enumerate(board):
        for column_index, value in enumerate(row):
            parts.append(
                _value_cell_html(
                    str(value),
                    theme,
                    is_dark_square(row_index, column_index),
                    font_size,
                    font_weight,
                )
            )
    return "".join(parts)


def _axis_label_html(value: str, theme: BoardTheme, font_size: str) -> str:
    return (
        '<div style="display:flex; align-items:center; justify-content:center; color:{color}; '
        'font-family:Calibri, Segoe UI, sans-serif; font-size:{font_size}; font-weight:700; '
        'line-height:1; box-sizing:border-box;">{value}</div>'
    ).format(
        color=theme.axis_text,
        font_size=font_size,
        value=escape(value),
    )


def _value_cell_html(
    value: str,
    theme: BoardTheme,
    is_dark: bool,
    font_size: str,
    font_weight: int = 800,
) -> str:
    background_style = _dark_cell_background_style(theme) if is_dark else f"background:{theme.light_cell};"
    resolved_font_size = _value_font_size_css(font_size, value)
    letter_spacing = _value_letter_spacing_css(value)
    return (
        '<div style="display:flex; align-items:center; justify-content:center; {background_style} '
        'color:{color}; font-family:Calibri, Segoe UI, sans-serif; font-size:{font_size}; '
        'font-weight:{font_weight}; line-height:0.95; letter-spacing:{letter_spacing}; '
        'box-sizing:border-box;">{value}</div>'
    ).format(
        background_style=background_style,
        color=theme.cell_text,
        font_size=resolved_font_size,
        font_weight=font_weight,
        letter_spacing=letter_spacing,
        value=escape(value),
    )


def _value_font_size_css(base_font_size: str, value: str) -> str:
    digit_count = len(value.lstrip("-"))
    if digit_count <= 1:
        scale = 1.08
    elif digit_count == 2:
        scale = 1.0
    elif digit_count == 3:
        scale = 0.84
    else:
        scale = 0.70
    return f"calc(({base_font_size}) * {scale:.2f})"


def _value_letter_spacing_css(value: str) -> str:
    digit_count = len(value.lstrip("-"))
    if digit_count <= 2:
        return "-0.01em"
    if digit_count == 3:
        return "-0.03em"
    return "-0.05em"


def _dark_cell_background_style(theme: BoardTheme) -> str:
    return (
        "background-color:{dark_cell}; "
        "background-image:repeating-linear-gradient(135deg, transparent 0 7px, {hatch_color} 7px 9px);"
    ).format(dark_cell=theme.dark_cell, hatch_color=theme.hatch_color)


def _route_overlay_html(
    route_squares: Sequence[tuple[int, int]] | None,
    theme: BoardTheme,
) -> str:
    if route_squares is None or len(route_squares) < 2:
        return ""

    points = " ".join(_svg_point(square) for square in route_squares)
    return (
        '<svg viewBox="0 0 800 800" preserveAspectRatio="none" '
        'style="position:absolute; inset:0; width:100%; height:100%; pointer-events:none; z-index:2;">'
        '<polyline points="{points}" fill="none" stroke="{outer}" stroke-width="20" '
        'stroke-linecap="round" stroke-linejoin="round" opacity="0.34" />'
        '<polyline points="{points}" fill="none" stroke="{inner}" stroke-width="12" '
        'stroke-linecap="round" stroke-linejoin="round" opacity="0.92" />'
        '</svg>'
    ).format(points=points, outer=theme.frame_inner, inner=theme.axis_text)


def _highlight_overlay_html(
    highlight_squares: Sequence[tuple[int, int]] | None,
    theme: BoardTheme,
) -> str:
    if not highlight_squares:
        return ""

    parts = [
        '<svg viewBox="0 0 800 800" preserveAspectRatio="none" '
        'style="position:absolute; inset:0; width:100%; height:100%; pointer-events:none; z-index:1;">'
    ]
    for row_index, column_index in highlight_squares:
        x_position = (column_index * 100) + 8
        y_position = (row_index * 100) + 8
        parts.append(
            (
                '<rect x="{x}" y="{y}" width="84" height="84" rx="16" fill="{fill}" fill-opacity="0.14" '
                'stroke="{stroke}" stroke-opacity="0.94" stroke-width="6" />'
                '<rect x="{x}" y="{y}" width="84" height="84" rx="16" fill="none" stroke="#ffffff" '
                'stroke-opacity="0.72" stroke-width="2" />'
            ).format(x=x_position, y=y_position, fill=theme.axis_text, stroke=theme.frame_inner)
        )
    parts.append("</svg>")
    return "".join(parts)


def _marker_overlay_html(
    start_square: tuple[int, int] | None,
    end_square: tuple[int, int] | None,
) -> str:
    if start_square is None and end_square is None:
        return ""

    parts = [
        '<svg viewBox="0 0 800 800" preserveAspectRatio="none" '
        'style="position:absolute; inset:0; width:100%; height:100%; pointer-events:none; z-index:3;">'
    ]

    start_badge_offset = -48.0
    end_badge_offset = -48.0
    start_radius = 36.0
    end_radius = 36.0
    if start_square is not None and end_square is not None and start_square == end_square:
        end_badge_offset = 18.0
        end_radius = 24.0

    if start_square is not None:
        parts.append(
            _marker_svg_html(
                start_square,
                "Start",
                START_MARKER_FILL,
                START_MARKER_STROKE,
                start_badge_offset,
                start_radius,
            )
        )
    if end_square is not None:
        parts.append(
            _marker_svg_html(
                end_square,
                "Slut",
                END_MARKER_FILL,
                END_MARKER_STROKE,
                end_badge_offset,
                end_radius,
            )
        )

    parts.append("</svg>")
    return "".join(parts)


def _marker_svg_html(
    square: tuple[int, int],
    label: str,
    fill: str,
    stroke: str,
    badge_offset_y: float,
    ring_radius: float,
) -> str:
    x_position, y_position = _route_center(square)
    badge_width = 36 + (len(label) * 12)
    badge_height = 28
    badge_x = x_position - (badge_width / 2)
    badge_y = y_position + badge_offset_y
    text_y = badge_y + 19
    return (
        '<circle cx="{x:.1f}" cy="{y:.1f}" r="{outer_radius:.1f}" fill="none" stroke="#ffffff" '
        'stroke-width="18" opacity="0.92" />'
        '<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="none" stroke="{stroke}" stroke-width="10" />'
        '<rect x="{badge_x:.1f}" y="{badge_y:.1f}" width="{badge_width:.1f}" height="{badge_height}" '
        'rx="14" fill="{fill}" stroke="#ffffff" stroke-width="3" />'
        '<text x="{x:.1f}" y="{text_y:.1f}" fill="#ffffff" text-anchor="middle" '
        'font-family="Calibri, Segoe UI, sans-serif" font-size="18" font-weight="700">{label}</text>'
    ).format(
        x=x_position,
        y=y_position,
        radius=ring_radius,
        outer_radius=ring_radius + 7,
        stroke=stroke,
        badge_x=badge_x,
        badge_y=badge_y,
        badge_width=badge_width,
        badge_height=badge_height,
        fill=fill,
        text_y=text_y,
        label=escape(label),
    )


def _svg_point(square: tuple[int, int]) -> str:
    x, y = _route_center(square)
    return f"{x:.1f},{y:.1f}"


def _route_center(square: tuple[int, int]) -> tuple[float, float]:
    row_index, column_index = square
    return (
        ((column_index + 0.5) / BOARD_AXIS) * 800,
        ((row_index + 0.5) / BOARD_AXIS) * 800,
    )
