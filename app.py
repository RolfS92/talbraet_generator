from __future__ import annotations

import streamlit as st

from board_app.branding import DEFAULT_WORKSHEET_TITLE
from board_app.exporters import board_to_json, board_to_pdf_bytes, board_to_png_bytes
from board_app.generators import generate_board, validate_board
from board_app.hidden_table import (
    DEFAULT_HIDDEN_TABLE_DIRECTION,
    HIDDEN_TABLE_DIRECTIONS,
    hidden_table_direction_label,
)
from board_app.knight_utils import format_square
from board_app.models import (
    BoardConfig,
    BoardType,
    CyclicConfig,
    HiddenTableConfig,
    KingTableConfig,
    KnightTableConfig,
)
from board_app.page_formats import DEFAULT_PAGE_FORMAT_LABEL, PAGE_FORMATS, PAGE_FORMATS_BY_LABEL, PageFormat
from board_app.presets import PRESETS, PRESETS_BY_LABEL, Preset, preset_table_rows
from board_app.rendering import board_to_table_html
from board_app.route_motifs import (
    DEFAULT_ROUTE_MOTIF,
    MOTIF_OPTIONS,
    ROUTE_MODE_MOTIF,
    motif_label,
)
from board_app.themes import DEFAULT_THEME_LABEL, THEMES, THEMES_BY_LABEL, BoardTheme

st.set_page_config(page_title="Talbræt-generator", layout="wide")

STATE_KEYS = {
    "sequence_min": "cyclic_sequence_min",
    "sequence_max": "cyclic_sequence_max",
    "table_spacing": "cyclic_table_spacing",
    "row_shift": "cyclic_row_shift",
    "custom_table_factor": "custom_table_factor",
    "hidden_table_factor": "hidden_table_factor",
    "hidden_start_square": "hidden_start_square",
    "hidden_direction": "hidden_direction",
    "hidden_random_between": "hidden_random_between",
    "hidden_show_table": "hidden_show_table",
    "route_table_factor": "route_table_factor",
    "route_start_square": "route_start_square",
    "route_end_square": "route_end_square",
    "route_move_count": "route_move_count",
    "route_mode": "route_mode",
    "route_motif": "route_motif",
    "route_show_path": "route_show_path",
    "route_show_markers": "route_show_markers",
    "page_format": "page_format",
    "title_auto": "worksheet_title_auto",
    "title_last_auto": "worksheet_title_last_auto",
}


def main() -> None:
    _ensure_title_state()
    _ensure_input_state()

    st.title("Talbræt-generator")
    st.caption("Talbræt med temaer og eksport til JSON, PNG og PDF.")
    st.info(
        "Til matematiklærere: Brug appen til hurtigt at lave talbrætter til træning af tabeller, mønstre og logiske ruter. "
        "Vælg en opsætning, generér et nyt bræt, og hent det klar til print i A4 eller A3."
    )

    selected_preset_label = st.sidebar.selectbox(
        "Preset",
        options=[preset.label for preset in PRESETS],
        index=0,
    )
    selected_preset = PRESETS_BY_LABEL[selected_preset_label]
    preset_changed = _sync_defaults_for_selected_preset(selected_preset, None)

    custom_table_factor = None
    if selected_preset.key == "custom_table":
        custom_table_factor = int(
            st.sidebar.number_input("Tabel", min_value=1, step=1, key=STATE_KEYS["custom_table_factor"])
        )
    elif selected_preset.key == "hidden_table":
        st.sidebar.number_input("Tabel", min_value=2, step=1, key=STATE_KEYS["hidden_table_factor"])
    elif selected_preset.board_type in (BoardType.KNIGHT_TABLE, BoardType.KING_TABLE):
        st.sidebar.number_input("Tabel", min_value=2, step=1, key=STATE_KEYS["route_table_factor"])
    if selected_preset.key == "motif_table":
        st.sidebar.selectbox(
            "Motiv",
            options=MOTIF_OPTIONS,
            key=STATE_KEYS["route_motif"],
            format_func=motif_label,
        )

    selected_theme_label = st.sidebar.selectbox(
        "Farvetema",
        options=[theme.label for theme in THEMES],
        index=_theme_index(DEFAULT_THEME_LABEL),
    )
    selected_theme = THEMES_BY_LABEL[selected_theme_label]
    _render_theme_button_css(selected_theme)
    selected_page_format_label = st.sidebar.selectbox(
        "Udskriftsformat",
        options=[page_format.label for page_format in PAGE_FORMATS],
        index=_page_format_index(st.session_state[STATE_KEYS["page_format"]]),
        key=STATE_KEYS["page_format"],
    )
    selected_page_format = PAGE_FORMATS_BY_LABEL[selected_page_format_label]
    show_route = False
    show_start_end = False
    show_hidden_table = False
    if selected_preset.board_type in (BoardType.KNIGHT_TABLE, BoardType.KING_TABLE):
        show_route = st.sidebar.checkbox("Vis rute", key=STATE_KEYS["route_show_path"])
        show_start_end = st.sidebar.checkbox("Vis start/slut", key=STATE_KEYS["route_show_markers"])
    elif selected_preset.key == "hidden_table":
        show_hidden_table = st.sidebar.checkbox("Vis tabel", key=STATE_KEYS["hidden_show_table"])

    st.sidebar.caption(_preset_description(selected_preset, custom_table_factor))
    _sync_title_with_settings(selected_preset, custom_table_factor)
    st.sidebar.text_input("Titel", key="worksheet_title", on_change=_handle_title_change)
    _ensure_board_state(selected_preset, custom_table_factor)

    if preset_changed:
        _generate_and_store_board(
            _config_from_preset(selected_preset, custom_table_factor),
            _preset_runtime_label(selected_preset, custom_table_factor),
        )

    submitted_config = _render_config_form(selected_preset, custom_table_factor)
    if submitted_config is not None:
        _generate_and_store_board(
            submitted_config,
            _preset_runtime_label(selected_preset, custom_table_factor),
        )

    current_title: str = st.session_state["worksheet_title"]
    current_preset_label: str = st.session_state["current_preset_label"]
    current_config: BoardConfig = st.session_state["current_config"]
    current_board = st.session_state["current_board"]
    current_issues = st.session_state["current_issues"]
    current_route_path = _route_squares_for_config(current_config, current_board)
    current_highlight_squares = _highlight_squares_for_config(current_config) if show_hidden_table else None
    current_start_square, current_end_square = (
        _route_markers_from_route(current_route_path) if show_start_end else (None, None)
    )
    current_route_squares = current_route_path if show_route else None

    left_column, right_column = st.columns([1.7, 1], gap="large")

    with left_column:
        st.subheader("Talbræt")
        st.caption(_board_description(current_config, show_route, show_start_end, show_hidden_table))
        st.markdown(
            board_to_table_html(
                current_board,
                selected_theme,
                highlight_squares=current_highlight_squares,
                route_squares=current_route_squares,
                start_square=current_start_square,
                end_square=current_end_square,
            ),
            unsafe_allow_html=True,
        )

    with right_column:
        st.subheader("Validering")
        if current_issues:
            for issue in current_issues:
                st.error(issue)
        else:
            st.success("Brættet opfylder de valgte regler.")

        st.subheader("Opsummering")
        _render_summary(
            current_title,
            current_preset_label,
            current_config,
            current_board,
            selected_theme,
            selected_page_format,
        )

        st.subheader("Eksport")
        json_payload = board_to_json(
            current_config,
            current_board,
            current_preset_label,
            current_title,
            selected_theme,
            selected_page_format,
        )
        png_payload = board_to_png_bytes(
            current_board,
            current_title,
            selected_theme,
            current_highlight_squares,
            current_route_squares,
            selected_page_format,
            current_start_square,
            current_end_square,
        )
        pdf_payload = board_to_pdf_bytes(
            current_board,
            current_title,
            selected_theme,
            current_highlight_squares,
            current_route_squares,
            selected_page_format,
            current_start_square,
            current_end_square,
        )
        slug = _slugify(current_title or current_preset_label)

        st.download_button(
            "Download JSON",
            data=json_payload,
            file_name=f"{slug}_{selected_page_format.key}_board.json",
            mime="application/json",
            use_container_width=True,
        )
        st.download_button(
            f"Download PNG ({selected_page_format.key.upper()})",
            data=png_payload,
            file_name=f"{slug}_{selected_page_format.key}_board.png",
            mime="image/png",
            use_container_width=True,
        )
        st.download_button(
            f"Download PDF ({selected_page_format.key.upper()})",
            data=pdf_payload,
            file_name=f"{slug}_{selected_page_format.key}_board.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        with st.expander("Vis JSON-preview"):
            st.code(json_payload, language="json")

    st.subheader("Presetoversigt")
    st.table(preset_table_rows())


def _render_config_form(preset: Preset, custom_table_factor: int | None) -> BoardConfig | None:
    with st.sidebar.form("config_form"):
        st.subheader("Konfiguration")
        if preset.board_type == BoardType.CYCLIC:
            active_step = int(_preset_defaults(preset, custom_table_factor)["sequence_step"])
            st.caption(f"Aktivt tabelspring: {active_step}")
            config: BoardConfig = CyclicConfig(
                sequence_min=int(st.number_input("Laveste tal på brættet", step=1, key=STATE_KEYS["sequence_min"])),
                sequence_max=int(st.number_input("Højeste tal på brættet", step=1, key=STATE_KEYS["sequence_max"])),
                sequence_step=active_step,
                row_shift=int(st.number_input("Forskydning per række", step=1, key=STATE_KEYS["row_shift"])),
            )
            st.caption(f"Eksempel: {active_step} {active_step * 2} {active_step * 3} {active_step * 4}")
        elif preset.board_type == BoardType.HIDDEN_TABLE:
            table_factor = int(st.session_state[STATE_KEYS["hidden_table_factor"]])
            random_between_count = int(
                st.number_input(
                    "Tilfældige tal mellem tabel",
                    min_value=1,
                    max_value=62,
                    step=1,
                    key=STATE_KEYS["hidden_random_between"],
                )
            )
            config = HiddenTableConfig(
                table_factor=table_factor,
                start_square=st.text_input("Startfelt", key=STATE_KEYS["hidden_start_square"]).strip().lower(),
                direction=st.selectbox(
                    "Retning",
                    options=HIDDEN_TABLE_DIRECTIONS,
                    key=STATE_KEYS["hidden_direction"],
                    format_func=hidden_table_direction_label,
                ),
                random_between_count=random_between_count,
            )
            st.caption("Kun de skjulte tabeltal følger tabellen. Alle andre felter bliver tilfældige tal tæt på tabellen.")
            st.caption("Retningen fortsætter gennem hele brættet: mod højre fortsætter på næste række, og nedad fortsætter i næste kolonne.")
            st.caption(_hidden_table_example(table_factor, random_between_count))
        elif preset.board_type == BoardType.KNIGHT_TABLE:
            table_factor = int(st.session_state[STATE_KEYS["route_table_factor"]])
            st.caption("Kun springerruten bliver tabeltal. Alle andre felter bliver random ikke-tabelltal.")
            st.caption(f"Aktiv tabel: {table_factor}-tabellen")
            config = KnightTableConfig(
                table_factor=table_factor,
            )
            config.start_square = st.text_input("Startfelt", key=STATE_KEYS["route_start_square"]).strip().lower()
            config.end_square = st.text_input("Slutfelt", key=STATE_KEYS["route_end_square"]).strip().lower()
            config.move_count = int(
                st.number_input("Antal spring", min_value=0, max_value=31, step=1, key=STATE_KEYS["route_move_count"])
            )
            st.caption(
                f"Ruten starter på `{config.table_factor}` og slutter på `{config.route_values()[-1]}` "
                f"ved `{config.move_count}` faktiske spring."
            )
            st.caption("Lige antal spring kræver samme feltfarve. Ulige antal spring kræver forskellig feltfarve.")
        elif preset.board_type == BoardType.KING_TABLE:
            table_factor = int(st.session_state[STATE_KEYS["route_table_factor"]])
            route_mode = ROUTE_MODE_MOTIF if preset.key == "motif_table" else "free"
            st.caption("Kun kongeruten bliver tabeltal. Alle andre felter bliver random ikke-tabelltal.")
            st.caption(f"Aktiv tabel: {table_factor}-tabellen")
            config = KingTableConfig(
                table_factor=table_factor,
                route_mode=route_mode,
                route_motif=str(st.session_state[STATE_KEYS["route_motif"]]),
            )
            if preset.key == "motif_table":
                st.caption(
                    f"Motivet `{motif_label(config.route_motif)}` bestemmer rutens form og længde."
                )
                st.caption("Start og slut bliver sat automatisk af den genererede rute, og rækkefølgen skifter fra bræt til bræt.")
            else:
                config.start_square = st.text_input("Startfelt", key=STATE_KEYS["route_start_square"]).strip().lower()
                config.end_square = st.text_input("Slutfelt", key=STATE_KEYS["route_end_square"]).strip().lower()
                config.move_count = int(
                    st.number_input("Antal træk", min_value=0, max_value=31, step=1, key=STATE_KEYS["route_move_count"])
                )
                st.caption(
                    f"Ruten starter på `{config.table_factor}` og slutter på `{config.route_values()[-1]}` "
                    f"ved `{config.move_count}` faktiske træk."
                )
                st.caption("En konge må rykke ét felt i alle otte retninger, og ruten bliver genereret tilfældigt.")
        else:
            raise ValueError(f"Ukendt board-type i UI: {preset.board_type}")

        submitted = st.form_submit_button("Generer nyt bræt", use_container_width=True)
        if submitted:
            return config
    return None


def _render_summary(
    title: str,
    preset_label: str,
    config: BoardConfig,
    board: list[list[int]],
    theme: BoardTheme,
    page_format: PageFormat,
) -> None:
    flat_values = [value for row in board for value in row]

    st.write(f"Titel: `{title}`")
    st.write(f"Preset: `{preset_label}`")
    st.write(f"Farvetema: `{theme.label}`")
    st.write(f"Udskriftsformat: `{page_format.label}`")
    st.write(f"Type: `{config.label}`")
    st.write(f"Min / maks på brættet: `{min(flat_values)}` / `{max(flat_values)}`")
    if isinstance(config, CyclicConfig):
        rule_text = (
            "Regel: sekvens "
            f"`{config.sequence_min}-{config.sequence_max}` i spring af `{config.sequence_step}` "
            f"med forskydning `{config.row_shift}` mellem rækker."
        )
        if config.has_random_slots():
            rule_text = (
                "Regel: sekvens "
                f"`{config.sequence_min}-{config.sequence_max}` i spring af `{config.sequence_step}`, "
                f"random mellem tabeltal med `n={config.table_spacing}` og forskydning `{config.row_shift}` mellem rækker."
            )
        st.write(rule_text)
    elif isinstance(config, HiddenTableConfig):
        st.write(
            f"Regel: `{config.table_factor}`-tabellen starter på `{config.start_square}` og går `{hidden_table_direction_label(config.direction).lower()}`."
        )
        st.write(
            f"Mellem hvert tabeltal ligger der `{config.random_between_count}` tilfældige tal tæt på tabellen."
        )
        st.write(
            f"Skjulte tabeltal: `{config.table_values()[0]}` til `{config.table_values()[-1]}` på `{len(config.table_values())}` felter."
        )
    elif isinstance(config, KnightTableConfig):
        st.write(
            f"Regel: kun `{len(config.route_values())}` felter fra `{config.table_factor}`-tabellen "
            f"på selve springerruten. Alle andre felter er random uden for tabellen."
        )
        st.write(
            f"Springerrute: `{config.start_square}` til `{config.end_square}` på `{config.move_count}` træk."
        )
        st.write(
            f"Rutetal: `{config.route_values()[0]}` til `{config.route_values()[-1]}` i stigende rækkefølge."
        )
    elif isinstance(config, KingTableConfig):
        st.write(
            f"Regel: kun `{len(config.route_values())}` felter fra `{config.table_factor}`-tabellen "
            f"på selve kongeruten. Alle andre felter er random uden for tabellen."
        )
        if config.route_mode == ROUTE_MODE_MOTIF:
            route_squares = config.route_squares_from_board(board)
            st.write(f"Motiv: `{motif_label(config.route_motif)}`.")
            if route_squares:
                st.write(
                    f"Genereret start/slut: `{format_square(route_squares[0])}` til `{format_square(route_squares[-1])}`."
                )
        else:
            st.write(
                f"Kongerute: `{config.start_square}` til `{config.end_square}` på `{config.move_count}` træk."
            )
        st.write(
            f"Rutetal: `{config.route_values()[0]}` til `{config.route_values()[-1]}` i stigende rækkefølge."
        )


def _generate_and_store_board(config: BoardConfig, preset_label: str) -> None:
    input_issues = config.validate()
    if input_issues:
        st.session_state["current_issues"] = input_issues
        return

    board = generate_board(config)
    rule_issues = validate_board(board, config)
    st.session_state["current_preset_label"] = preset_label
    st.session_state["current_config"] = config
    st.session_state["current_board"] = board
    st.session_state["current_issues"] = rule_issues


def _ensure_board_state(default_preset: Preset, custom_table_factor: int | None) -> None:
    if all(
        key in st.session_state
        for key in ("current_preset_label", "current_config", "current_board", "current_issues")
    ):
        return

    default_config = _config_from_preset(default_preset, custom_table_factor)
    st.session_state["current_preset_label"] = _preset_runtime_label(default_preset, custom_table_factor)
    st.session_state["current_config"] = default_config
    st.session_state["current_board"] = generate_board(default_config)
    st.session_state["current_issues"] = []


def _ensure_title_state() -> None:
    if "worksheet_title" not in st.session_state:
        st.session_state["worksheet_title"] = DEFAULT_WORKSHEET_TITLE
    if STATE_KEYS["title_auto"] not in st.session_state:
        st.session_state[STATE_KEYS["title_auto"]] = True
    if STATE_KEYS["title_last_auto"] not in st.session_state:
        st.session_state[STATE_KEYS["title_last_auto"]] = DEFAULT_WORKSHEET_TITLE


def _ensure_input_state() -> None:
    if STATE_KEYS["custom_table_factor"] not in st.session_state:
        st.session_state[STATE_KEYS["custom_table_factor"]] = 5
    if STATE_KEYS["sequence_min"] not in st.session_state:
        st.session_state[STATE_KEYS["sequence_min"]] = 5
    if STATE_KEYS["sequence_max"] not in st.session_state:
        st.session_state[STATE_KEYS["sequence_max"]] = 40
    if STATE_KEYS["table_spacing"] not in st.session_state:
        st.session_state[STATE_KEYS["table_spacing"]] = 2
    if STATE_KEYS["row_shift"] not in st.session_state:
        st.session_state[STATE_KEYS["row_shift"]] = 1
    if STATE_KEYS["hidden_table_factor"] not in st.session_state:
        st.session_state[STATE_KEYS["hidden_table_factor"]] = 4
    if STATE_KEYS["hidden_start_square"] not in st.session_state:
        st.session_state[STATE_KEYS["hidden_start_square"]] = "a8"
    if STATE_KEYS["hidden_direction"] not in st.session_state:
        st.session_state[STATE_KEYS["hidden_direction"]] = DEFAULT_HIDDEN_TABLE_DIRECTION
    if STATE_KEYS["hidden_random_between"] not in st.session_state:
        st.session_state[STATE_KEYS["hidden_random_between"]] = 4
    if STATE_KEYS["hidden_show_table"] not in st.session_state:
        st.session_state[STATE_KEYS["hidden_show_table"]] = True
    if STATE_KEYS["route_table_factor"] not in st.session_state:
        st.session_state[STATE_KEYS["route_table_factor"]] = 4
    if STATE_KEYS["route_start_square"] not in st.session_state:
        st.session_state[STATE_KEYS["route_start_square"]] = "a7"
    if STATE_KEYS["route_end_square"] not in st.session_state:
        st.session_state[STATE_KEYS["route_end_square"]] = "h8"
    if STATE_KEYS["route_move_count"] not in st.session_state:
        st.session_state[STATE_KEYS["route_move_count"]] = 10
    if STATE_KEYS["route_mode"] not in st.session_state:
        st.session_state[STATE_KEYS["route_mode"]] = "free"
    if STATE_KEYS["route_motif"] not in st.session_state:
        st.session_state[STATE_KEYS["route_motif"]] = DEFAULT_ROUTE_MOTIF
    if STATE_KEYS["route_show_path"] not in st.session_state:
        st.session_state[STATE_KEYS["route_show_path"]] = True
    if STATE_KEYS["route_show_markers"] not in st.session_state:
        st.session_state[STATE_KEYS["route_show_markers"]] = True
    if STATE_KEYS["page_format"] not in st.session_state:
        st.session_state[STATE_KEYS["page_format"]] = DEFAULT_PAGE_FORMAT_LABEL


def _sync_defaults_for_selected_preset(preset: Preset, custom_table_factor: int | None) -> bool:
    signature = _preset_signature(preset, custom_table_factor)
    previous_signature = st.session_state.get("active_preset_signature")
    previous_preset_key = st.session_state.get("active_preset_key")
    if previous_signature == signature:
        return False

    if previous_preset_key != preset.key or preset.key == "custom_table":
        defaults = _preset_defaults(preset, custom_table_factor)
        for field_name, value in defaults.items():
            state_key = _state_key_for_field(field_name, preset)
            if state_key is None:
                continue
            st.session_state[state_key] = value

    st.session_state["active_preset_key"] = preset.key
    st.session_state["active_preset_signature"] = signature
    return True


def _config_from_preset(preset: Preset, custom_table_factor: int | None) -> BoardConfig:
    if preset.board_type == BoardType.CYCLIC:
        return CyclicConfig(**_preset_defaults(preset, custom_table_factor))
    if preset.board_type == BoardType.HIDDEN_TABLE:
        return HiddenTableConfig(
            table_factor=int(st.session_state[STATE_KEYS["hidden_table_factor"]]),
            start_square=str(st.session_state[STATE_KEYS["hidden_start_square"]]).strip().lower(),
            direction=str(st.session_state[STATE_KEYS["hidden_direction"]]),
            random_between_count=int(st.session_state[STATE_KEYS["hidden_random_between"]]),
        )
    if preset.board_type == BoardType.KNIGHT_TABLE:
        return KnightTableConfig(
            table_factor=int(st.session_state[STATE_KEYS["route_table_factor"]]),
            start_square=str(st.session_state[STATE_KEYS["route_start_square"]]).strip().lower(),
            end_square=str(st.session_state[STATE_KEYS["route_end_square"]]).strip().lower(),
            move_count=int(st.session_state[STATE_KEYS["route_move_count"]]),
        )
    if preset.board_type == BoardType.KING_TABLE:
        route_mode = ROUTE_MODE_MOTIF if preset.key == "motif_table" else "free"
        return KingTableConfig(
            table_factor=int(st.session_state[STATE_KEYS["route_table_factor"]]),
            start_square=str(st.session_state[STATE_KEYS["route_start_square"]]).strip().lower(),
            end_square=str(st.session_state[STATE_KEYS["route_end_square"]]).strip().lower(),
            move_count=int(st.session_state[STATE_KEYS["route_move_count"]]),
            route_mode=route_mode,
            route_motif=str(st.session_state[STATE_KEYS["route_motif"]]),
        )
    raise ValueError(f"Ukendt board-type i preset: {preset.board_type}")


def _preset_defaults(preset: Preset, custom_table_factor: int | None) -> dict[str, object]:
    if preset.key != "custom_table":
        return dict(preset.defaults)

    factor = custom_table_factor or int(st.session_state[STATE_KEYS["custom_table_factor"]])
    current_row_shift = int(st.session_state.get(STATE_KEYS["row_shift"], 1))
    return {
        "sequence_min": factor,
        "sequence_max": factor * 8,
        "sequence_step": factor,
        "table_spacing": 2,
        "row_shift": current_row_shift,
    }


def _preset_runtime_label(preset: Preset, custom_table_factor: int | None) -> str:
    if preset.key != "custom_table":
        if preset.key == "hidden_table":
            factor = int(st.session_state[STATE_KEYS["hidden_table_factor"]])
            return f"Find den skjulte tabel {factor}-tabel"
        if preset.key == "knight_table":
            factor = int(st.session_state[STATE_KEYS["route_table_factor"]])
            return f"Springerrute {factor}-tabel"
        if preset.key == "king_table":
            factor = int(st.session_state[STATE_KEYS["route_table_factor"]])
            return f"Kongerute {factor}-tabel"
        if preset.key == "motif_table":
            factor = int(st.session_state[STATE_KEYS["route_table_factor"]])
            return f"Motiv {motif_label(str(st.session_state[STATE_KEYS['route_motif']])).lower()} {factor}-tabel"
        return preset.label
    factor = custom_table_factor or int(st.session_state[STATE_KEYS["custom_table_factor"]])
    return f"{factor}-tabellen"


def _preset_description(preset: Preset, custom_table_factor: int | None) -> str:
    if preset.key == "hidden_table":
        factor = int(st.session_state[STATE_KEYS["hidden_table_factor"]])
        start_square = str(st.session_state[STATE_KEYS["hidden_start_square"]]).strip().lower()
        direction = hidden_table_direction_label(str(st.session_state[STATE_KEYS["hidden_direction"]])).lower()
        random_between_count = int(st.session_state[STATE_KEYS["hidden_random_between"]])
        return (
            f"Find {factor}-tabellen fra {start_square} {direction}. "
            f"Der ligger {random_between_count} tilfældige tal mellem hvert tabeltal."
        )
    if preset.key == "knight_table":
        factor = int(st.session_state[STATE_KEYS["route_table_factor"]])
        start_square = str(st.session_state[STATE_KEYS["route_start_square"]]).strip().lower()
        end_square = str(st.session_state[STATE_KEYS["route_end_square"]]).strip().lower()
        move_count = int(st.session_state[STATE_KEYS["route_move_count"]])
        return (
            f"Kun springerruten bruger {factor}-tabellen. "
            f"Springerrute: {start_square} -> {end_square} på {move_count} træk."
        )
    if preset.key == "king_table":
        factor = int(st.session_state[STATE_KEYS["route_table_factor"]])
        start_square = str(st.session_state[STATE_KEYS["route_start_square"]]).strip().lower()
        end_square = str(st.session_state[STATE_KEYS["route_end_square"]]).strip().lower()
        move_count = int(st.session_state[STATE_KEYS["route_move_count"]])
        return (
            f"Kun kongeruten bruger {factor}-tabellen. "
            f"Kongerute: {start_square} -> {end_square} på {move_count} træk."
        )
    if preset.key == "motif_table":
        factor = int(st.session_state[STATE_KEYS["route_table_factor"]])
        route_motif = motif_label(str(st.session_state[STATE_KEYS["route_motif"]]))
        return (
            f"Kun kongeruten bruger {factor}-tabellen. "
            f"Motiv: {route_motif}."
        )
    if preset.key != "custom_table":
        return preset.description
    factor = custom_table_factor or int(st.session_state[STATE_KEYS["custom_table_factor"]])
    return (
        "Vælg selv en tabel og bestem selv intervallet på brættet. "
        f"Eksempel: {factor} {factor * 2} {factor * 3} {factor * 4}"
    )


def _preset_signature(preset: Preset, custom_table_factor: int | None) -> str:
    if preset.key == "custom_table":
        factor = custom_table_factor or int(st.session_state[STATE_KEYS["custom_table_factor"]])
        return f"{preset.key}:{factor}"
    if preset.key == "hidden_table":
        factor = int(st.session_state[STATE_KEYS["hidden_table_factor"]])
        return f"{preset.key}:{factor}"
    if preset.key == "knight_table":
        factor = int(st.session_state[STATE_KEYS["route_table_factor"]])
        return f"{preset.key}:{factor}"
    if preset.key == "king_table":
        factor = int(st.session_state[STATE_KEYS["route_table_factor"]])
        return f"{preset.key}:{factor}"
    if preset.key == "motif_table":
        factor = int(st.session_state[STATE_KEYS["route_table_factor"]])
        route_motif = str(st.session_state[STATE_KEYS["route_motif"]])
        return f"{preset.key}:{factor}:{route_motif}"
    return preset.key


def _state_key_for_field(field_name: str, preset: Preset) -> str | None:
    if field_name == "table_factor":
        if preset.key == "hidden_table":
            return STATE_KEYS["hidden_table_factor"]
        return STATE_KEYS["route_table_factor"]
    if field_name == "start_square":
        if preset.key == "hidden_table":
            return STATE_KEYS["hidden_start_square"]
        return STATE_KEYS["route_start_square"]
    return {
        "sequence_min": STATE_KEYS["sequence_min"],
        "sequence_max": STATE_KEYS["sequence_max"],
        "table_spacing": STATE_KEYS["table_spacing"],
        "row_shift": STATE_KEYS["row_shift"],
        "direction": STATE_KEYS["hidden_direction"],
        "random_between_count": STATE_KEYS["hidden_random_between"],
        "show_table": STATE_KEYS["hidden_show_table"],
        "end_square": STATE_KEYS["route_end_square"],
        "move_count": STATE_KEYS["route_move_count"],
        "show_path": STATE_KEYS["route_show_path"],
        "route_mode": STATE_KEYS["route_mode"],
        "route_motif": STATE_KEYS["route_motif"],
    }.get(field_name)


def _theme_index(label: str) -> int:
    labels = [theme.label for theme in THEMES]
    return labels.index(label)


def _page_format_index(label: str) -> int:
    labels = [page_format.label for page_format in PAGE_FORMATS]
    if label not in labels:
        return labels.index(DEFAULT_PAGE_FORMAT_LABEL)
    return labels.index(label)


def _sync_title_with_settings(preset: Preset, custom_table_factor: int | None) -> None:
    auto_title = _suggested_title_from_settings(preset, custom_table_factor)
    st.session_state[STATE_KEYS["title_last_auto"]] = auto_title
    if st.session_state.get(STATE_KEYS["title_auto"], True):
        st.session_state["worksheet_title"] = auto_title


def _suggested_title_from_settings(preset: Preset, custom_table_factor: int | None) -> str:
    return _preset_runtime_label(preset, custom_table_factor)


def _handle_title_change() -> None:
    st.session_state[STATE_KEYS["title_auto"]] = (
        st.session_state.get("worksheet_title", "")
        == st.session_state.get(STATE_KEYS["title_last_auto"], "")
    )


def _render_theme_button_css(theme: BoardTheme) -> None:
    st.markdown(
        (
            "<style>"
            "div[data-testid='stSidebar'] button[kind='primary'],"
            "div[data-testid='stSidebar'] button[type='submit'] {"
            "background-color:%(background)s;"
            "border-color:%(border)s;"
            "color:#ffffff;"
            "}"
            "div[data-testid='stSidebar'] button[kind='primary']:hover,"
            "div[data-testid='stSidebar'] button[type='submit']:hover {"
            "background-color:%(hover)s;"
            "border-color:%(hover)s;"
            "color:#ffffff;"
            "}"
            "div[data-testid='stSidebar'] button[kind='primary']:focus,"
            "div[data-testid='stSidebar'] button[type='submit']:focus {"
            "box-shadow:0 0 0 0.2rem %(focus)s;"
            "outline:none;"
            "}"
            "</style>"
        )
        % {
            "background": theme.axis_text,
            "border": theme.axis_text,
            "hover": theme.frame_outer,
            "focus": _hex_to_rgba_css(theme.axis_text, 0.22),
        },
        unsafe_allow_html=True,
    )


def _hex_to_rgba_css(color: str, alpha: float) -> str:
    color = color.lstrip("#")
    if len(color) != 6:
        return f"rgba(0, 0, 0, {alpha})"
    return (
        f"rgba({int(color[0:2], 16)}, {int(color[2:4], 16)}, {int(color[4:6], 16)}, {alpha:.3f})"
    )


def _slugify(value: str) -> str:
    replacements = {
        "æ": "ae",
        "ø": "oe",
        "å": "aa",
        "Æ": "ae",
        "Ø": "oe",
        "Å": "aa",
    }
    characters = []
    for character in "".join(replacements.get(character, character) for character in value.lower()):
        if character.isalnum():
            characters.append(character)
        else:
            characters.append("_")
    return "".join(characters).strip("_") or "talbraet"


def _route_squares_for_config(
    config: BoardConfig,
    board: list[list[int]],
) -> list[tuple[int, int]] | None:
    if not isinstance(config, (KnightTableConfig, KingTableConfig)):
        return None
    return config.route_squares_from_board(board)


def _highlight_squares_for_config(config: BoardConfig) -> list[tuple[int, int]] | None:
    if not isinstance(config, HiddenTableConfig):
        return None
    return config.table_squares()


def _board_description(
    config: BoardConfig,
    show_route: bool,
    show_start_end: bool,
    show_hidden_table: bool,
) -> str:
    if isinstance(config, CyclicConfig):
        return (
            f"Et tabelbræt med {config.sequence_step}-tabellen fra {config.sequence_min} til {config.sequence_max} "
            f"og forskydning {config.row_shift} pr. række."
        )
    if isinstance(config, HiddenTableConfig):
        visibility_text = "Facit er vist." if show_hidden_table else "Facit er skjult."
        return (
            f"Find {config.table_factor}-tabellen fra {config.start_square} "
            f"{hidden_table_direction_label(config.direction).lower()} med {config.random_between_count} "
            f"tilfældige tal mellem hvert tabeltal. {visibility_text}"
        )
    if isinstance(config, KnightTableConfig):
        route_text = "Ruten er vist." if show_route else "Ruten er skjult."
        marker_text = "Start og slut er markeret." if show_start_end else "Start og slut er skjult."
        return (
            f"Følg {config.table_factor}-tabellen på en springerrute fra {config.start_square} "
            f"til {config.end_square} på {config.move_count} spring. {route_text} {marker_text}"
        )
    if isinstance(config, KingTableConfig):
        route_text = "Ruten er vist." if show_route else "Ruten er skjult."
        marker_text = "Start og slut er markeret." if show_start_end else "Start og slut er skjult."
        if config.route_mode == ROUTE_MODE_MOTIF:
            return (
                f"Følg {config.table_factor}-tabellen i motivet {motif_label(config.route_motif).lower()}. "
                f"{route_text}"
            )
        return (
            f"Følg {config.table_factor}-tabellen på en kongerute fra {config.start_square} "
            f"til {config.end_square} på {config.move_count} træk. {route_text} {marker_text}"
        )
    return "Talbræt klar til brug."


def _route_markers_from_route(
    route_squares: list[tuple[int, int]] | None,
) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    if not route_squares:
        return (None, None)
    return (route_squares[0], route_squares[-1])


def _hidden_table_example(table_factor: int, random_between_count: int) -> str:
    values = [table_factor, table_factor * 2, table_factor * 3]
    pieces = [str(values[0])]
    for next_value in values[1:]:
        pieces.extend(["(tilfældigt tal)" for _ in range(random_between_count)])
        pieces.append(str(next_value))
    return "Eksempel: " + " ".join(pieces)


if __name__ == "__main__":
    main()
