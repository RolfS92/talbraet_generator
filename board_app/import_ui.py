"""Reviewable image-to-board workflow; drafts never replace an approved board."""
from __future__ import annotations

from hashlib import sha256
import math

import pandas as pd
from PIL import ImageDraw
import streamlit as st

from board_app.generators import validate_board
from board_app.image_import import (
    ImageImportError, OCRUnavailableError, crop_board_image,
    load_board_image, recognize_board_image, suggest_board_crop,
)
from board_app.models import ImportedBoardConfig

COLUMNS = list("ABCDEFGH")


def editor_to_board(frame: pd.DataFrame) -> list[list[int]]:
    """Accept editor numeric scalars without rounding or filling missing cells."""
    if frame.shape != (8, 8):
        raise ValueError("Brættet skal have præcis 8 rækker og 8 kolonner.")
    board = []
    for r, row in enumerate(frame.itertuples(index=False, name=None)):
        values = []
        for c, value in enumerate(row):
            square = f"{COLUMNS[c]}{8-r}"
            if pd.isna(value):
                raise ValueError(f"Felt {square} mangler et tal. Udfyld alle 64 felter.")
            if isinstance(value, (bool, str)):
                raise ValueError(f"Felt {square} skal indeholde et heltal.")
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError):
                raise ValueError(f"Felt {square} skal indeholde et heltal.") from None
            if not math.isfinite(number) or not number.is_integer() or not -9999 <= number <= 9999:
                raise ValueError(f"Felt {square} skal være et heltal fra -9999 til 9999.")
            values.append(int(value))
        board.append(values)
    return board


def render_image_import() -> bool:
    st.subheader("Opret talbræt fra billede")
    st.write("Upload et billede, afgræns de 64 felter, og kontrollér tallene. Derefter får du brættet i samme layout og printformater som de øvrige talbrætter.")
    uploaded = st.file_uploader("Billede af et talbræt", type=["png", "jpg", "jpeg", "webp"],
                                help="PNG, JPG eller WebP. Højst 10 MB og 20 megapixels.")
    st.caption("Billedet behandles i appen uden en ekstern billed- eller AI-tjeneste.")
    if uploaded is None:
        return False
    image_bytes = uploaded.getvalue()
    file_id = sha256(image_bytes).hexdigest()[:16]
    try:
        source = load_board_image(image_bytes)
    except ImageImportError as exc:
        st.error(str(exc))
        return False

    st.markdown("**1. Afgræns brættet**")
    rotation = st.selectbox("Drej billedet med uret", [0, 90, 180, 270],
                            format_func=lambda degrees: f"{degrees}°", key=f"rotation_{file_id}")
    source = source.rotate(-rotation, expand=True)
    crop_key = f"{file_id}_{rotation}"
    if st.session_state.get("import_crop_source") != crop_key:
        st.session_state["import_crop_source"] = crop_key
        st.session_state["import_crop_suggestion"] = suggest_board_crop(source)
    suggestion = st.session_state["import_crop_suggestion"]
    initial = suggestion or (0, 0, source.width, source.height)
    if suggestion:
        st.caption("Brættets kanter er foreslået automatisk. Kontrollér og justér dem nedenfor.")
    st.caption("Afgræns kun selve de 8×8 felter. Udelad bogstaver, rækkenumre, ramme og tekst. Række 8 skal være øverst, A til venstre. Brug et foto taget lige ovenfra.")
    left, right = st.slider("Venstre og højre kant (pixels)", 0, source.width,
                            (initial[0], initial[2]), key=f"crop_x_{crop_key}")
    top, bottom = st.slider("Øverste og nederste kant (pixels)", 0, source.height,
                            (initial[1], initial[3]), key=f"crop_y_{crop_key}")
    source_preview = source.copy()
    ImageDraw.Draw(source_preview).rectangle((left, top, right, bottom), outline="#e03131", width=max(2, source.width // 250))
    source_preview.thumbnail((800, 600))
    preview_columns = st.columns(2)
    preview_columns[0].image(source_preview, caption="Det valgte område er markeret med rødt.")
    try:
        cropped = crop_board_image(source, (left, top, right, bottom))
    except ImageImportError as exc:
        st.info(str(exc))
        return False
    grid_preview = cropped.copy()
    grid_preview.thumbnail((600, 600))
    grid_draw = ImageDraw.Draw(grid_preview)
    for index in range(1, 8):
        x, y = round(index * grid_preview.width / 8), round(index * grid_preview.height / 8)
        grid_draw.line((x, 0, x, grid_preview.height), fill="#e03131", width=1)
        grid_draw.line((0, y, grid_preview.width, y), fill="#e03131", width=1)
    preview_columns[1].image(grid_preview, caption="Kontrollér, at de røde linjer følger felternes kanter.")
    signature = f"{crop_key}_{left}_{top}_{right}_{bottom}"
    if st.session_state.get("import_signature") != signature:
        st.session_state["import_signature"] = signature
        st.session_state.pop("import_draft", None)
        st.session_state.pop("import_approved", None)
        st.session_state["import_revision"] = st.session_state.get("import_revision", 0) + 1

    actions = st.columns(2)
    read = actions[0].button("Aflæs tal fra billedet", type="primary")
    manual = actions[1].button("Udfyld tallene manuelt")
    if read:
        try:
            with st.spinner("Aflæser de 64 felter …"):
                result = recognize_board_image(cropped)
            st.session_state["import_draft"] = result.values
            st.session_state["import_review_cells"] = result.review_cells
            st.session_state["import_revision"] += 1
            st.session_state.pop("import_approved", None)
        except (ImageImportError, OCRUnavailableError) as exc:
            st.error(str(exc))
            st.info("Du kan stadig udfylde tallene manuelt med billedet som reference.")
    if manual:
        st.session_state["import_draft"] = [[None] * 8 for _ in range(8)]
        st.session_state["import_review_cells"] = ()
        st.session_state["import_revision"] += 1
        st.session_state.pop("import_approved", None)
    if "import_draft" not in st.session_state:
        return False

    st.markdown("**2. Kontrollér og ret alle 64 tal**")
    st.caption("Række 8 står øverst og række 1 nederst. Dobbeltklik på et felt for at rette tallet. Tomme felter skal udfyldes. Sammenlign også de øvrige tal med billedet.")
    review = st.session_state.get("import_review_cells", ())
    if review:
        st.warning("Kontrollér især disse usikre eller manglende felter: " + ", ".join(s.upper() for s in review))
    draft = pd.DataFrame(st.session_state["import_draft"], index=range(8, 0, -1), columns=COLUMNS, dtype="float64")
    revision = st.session_state["import_revision"]
    # Group edits and approval in one form: an export always reflects one explicit approval.
    with st.form(f"import_review_{revision}"):
        edited = st.data_editor(
            draft, key=f"import_editor_{revision}", num_rows="fixed", use_container_width=True,
            column_config={column: st.column_config.NumberColumn(column, min_value=-9999,
                           max_value=9999, step=1, format="%d", required=True) for column in COLUMNS},
        )
        approved = st.session_state.get("import_approved")
        reviewed = st.checkbox("Jeg har kontrolleret alle 64 tal mod billedet",
                               value=bool(approved and approved[0] == signature),
                               key=f"reviewed_{revision}")
        apply = st.form_submit_button("Brug talbrættet", type="primary")
    if apply:
        st.session_state.pop("import_approved", None)
        if not reviewed:
            st.error("Kontrollér tallene og markér afkrydsningsfeltet, før du bruger brættet.")
            return False
        try:
            board = editor_to_board(edited)
        except ValueError as exc:
            st.error(str(exc))
            return False
        config = ImportedBoardConfig(source_name=uploaded.name)
        issues = validate_board(board, config)
        if issues:
            for issue in issues:
                st.error(issue)
            return False
        st.session_state["import_approved"] = (signature, board, config)
        # Widget edit deltas disappear when the user leaves import mode. Keep
        # the reviewed values as the next draft and use a fresh editor key so
        # old deltas cannot be reapplied to a changed dataframe.
        st.session_state["import_draft"] = [row.copy() for row in board]
        st.session_state["import_revision"] += 1
        st.rerun()
    approved = st.session_state.get("import_approved")
    if approved is None or approved[0] != signature:
        return False
    _, board, config = approved
    st.session_state["current_board"] = board
    st.session_state["current_config"] = config
    st.session_state["current_preset_label"] = "Importeret fra billede"
    st.session_state["current_issues"] = []
    st.success("Det godkendte talbræt er klar nedenfor. Nye rettelser træder i kraft, når du trykker Brug talbrættet igen.")
    return True
