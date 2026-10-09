from __future__ import annotations

from app.estilos import (
    CSS,
    alert_html,
    aside_html,
    chips_html,
    resumen_reporte_html,
    ficha_header_html,
    heading_html,
    section_html,
    tema_label,
    empty_draft_html,
    evidence_head_html,
    evidence_kv_html,
    hero_html,
    info_html,
    row_content_html,
    score_block_html,
)


def test_hero_escapes_nothing_dynamic_but_shows_the_three_kpis():
    html_out = hero_html(12, 3, 7)

    assert "Inteligencia editorial" in html_out
    assert ">12<" in html_out and ">3<" in html_out and ">7<" in html_out
    for label in ("Registros priorizados", "Prioridad alta", "Requieren evidencia"):
        assert label in html_out


def test_score_card_escapes_dynamic_text():
    html_out = row_content_html(
        rank=1,
        tema="<b>tema</b>",
        fecha="01/01/2026",
        titulo="<script>alert(1)</script>",
        chips=[("Evidencia <i>x</i>", "warn")],
    )

    assert "<script>" not in html_out
    assert "&lt;script&gt;" in html_out
    assert "<b>tema</b>" not in html_out
    assert "&lt;i&gt;" in html_out
    assert "chip warn" in html_out


def test_score_bar_width_is_clamped_to_0_100():
    assert "width:100%" in score_block_html(250.0)
    assert "width:0%" in score_block_html(-5.0)
    assert "Atención<b>90.0</b>" in score_block_html(90.0)


REAL_SUMMARY = (
    "R=1.0 (tema=servicios_publicos, medio_nacional=True); I=1.0 (alcance=nacional); "
    "U=1.0 (antigüedad vs fecha_ref); N=1.0 (repetición=no); "
    "E=0.0 (procedencias/fuente primaria; contexto oficial de nivel-tema no suma, "
    "ver contexto_oficial)"
)


def test_resumen_renders_five_rows_with_badge_chips_value_and_bar():
    out = resumen_reporte_html(REAL_SUMMARY, "Sin repetición detectada en este grupo.")

    assert out.count('class="rrow"') == 5
    for letter in "RIUNE":
        assert f'<div class="rbadge' in out and f">{letter}</div>" in out
    assert out.count('class="rval') == 5
    assert out.count('class="rbar') == 5
    # chips: key/value pairs, underscores shown as spaces, True -> Sí
    assert '<span class="rchip"><span>tema</span><b>servicios publicos</b></span>' in out
    assert "<b>Sí</b>" in out
    assert '<span class="rchip"><span>alcance</span><b>nacional</b></span>' in out
    # label-only criterion and its notes
    assert '<span class="rlabel">antigüedad vs fecha ref</span>' in out
    assert "procedencias/fuente primaria" in out
    assert "Contexto oficial de nivel-tema no suma, ver contexto_oficial." in out
    # footer note
    assert '<div class="rfoot">Sin repetición detectada en este grupo.</div>' in out


def test_resumen_highlights_only_zero_components_and_scales_the_bar():
    out = resumen_reporte_html(
        "R=1.0 (a=b); I=0.5 (a=b); U=0.25 (a=b); N=1.0 (a=b); E=0.0 (x)"
    )

    assert out.count('rbadge low') == 1 and out.count('rval low') == 1
    assert "width:100%" in out and "width:50%" in out and "width:25%" in out
    assert "width:0%" in out


def test_resumen_escapes_everything_and_falls_back_to_the_plain_text():
    out = resumen_reporte_html("R=1.0 (<script>x</script>=<b>y</b>)")
    assert "<script>" not in out and "&lt;script&gt;" in out

    fallback = resumen_reporte_html("formato <i>inesperado</i>", "pie")
    assert "<i>" not in fallback and "&lt;i&gt;inesperado" in fallback
    assert "Resumen del reporte" in fallback and "pie" in fallback
    assert 'class="rrow"' not in fallback


def test_aside_has_score_tiles_and_rules_but_no_component_breakdown():
    out = aside_html(
        puntaje=90.0,
        prioridad="<alto>",
        estado_evidencia="insuficiente",
        version_reglas="v0.3<",
    )

    assert ">90.0<" in out
    assert "<alto>" not in out
    assert "Insuficiente" in out
    assert "Reglas v0.3&lt;" in out
    assert "Componentes" not in out and 'class="comp' not in out


def test_ficha_header_alert_section_and_heading_escape_dynamic_text():
    header = ficha_header_html("<t>", "G-1<", "<script>x</script>")
    assert "<script>" not in header and "Registro editorial G-1&lt;" in header
    assert "Volver" not in header  # the back button is a native widget

    alert = alert_html("Prioridad <i>", "No es publicable.")
    assert "<i>" not in alert and "&lt;i&gt;" in alert and "No es publicable." in alert

    section = section_html("Resumen", "<i>cuerpo</i>")
    assert "<i>" not in section and "&lt;i&gt;cuerpo" in section

    assert "<script>" not in heading_html("<script>")
    assert chips_html([("<b>", "")]).count("&lt;b&gt;") == 1


def test_css_defines_the_design_tokens():
    for token in ("#f4f1ea", "#15171c", "#a3162f", "Newsreader", "Source Sans 3"):
        assert token in CSS


def test_info_html_escapes_text_label_and_link():
    out = info_html("<b>x</b>", "<i>t</i>", href="https://a.b/?q=1&r=\"2\"", link_text="<id>")

    assert 'class="info"' in out
    assert "<i>" not in out and "<b>x</b>" not in out
    assert "&lt;i&gt;" in out
    assert "&amp;r=" in out and "&quot;2&quot;" in out
    assert "&lt;id&gt;" in out


def test_info_html_without_label_or_link_is_just_the_text():
    out = info_html("", "Por verificar: algo")

    assert out.startswith('<div class="info"><svg')
    assert out.endswith("<div>Por verificar: algo</div></div>")
    assert "<b>" not in out


def test_empty_draft_html_keeps_the_exact_message():
    out = empty_draft_html()

    assert 'class="empty"' in out
    assert "Borrador no generado para este grupo (ejecutar <code>make generar</code>)." in out


def test_evidence_head_escapes_title_and_id():
    out = evidence_head_html("<script>x</script>", "N-1<", "titulo")

    assert "<script>" not in out
    assert "ID de evidencia: N-1&lt;" in out
    assert "Campo citado disponible: titulo" in out


def test_evidence_kv_marks_missing_values_and_escapes():
    out = evidence_kv_html([("Medio", "<b>TVN</b>"), ("Fecha", "No disponible")])

    assert "&lt;b&gt;TVN&lt;/b&gt;" in out
    assert out.count('class="v na"') == 1


def test_css_styles_expanders_chat_and_empty_states():
    for selector in ('stExpander', 'stChatInput', 'stChatMessage', ".kv", ".empty", ".info"):
        assert selector in CSS


def test_tema_label_uses_accented_names_and_falls_back_readably():
    assert tema_label("servicios_publicos") == "Servicios públicos"
    assert tema_label("tema_nuevo") == "Tema nuevo"
    assert "Servicios públicos" in row_content_html(1, "servicios_publicos", "f", "x", [])
    assert "Servicios públicos" in ficha_header_html("servicios_publicos", "G-1", "x")


def test_css_keeps_button_text_visible_in_every_state():
    for state in (":visited", ":focus:not(:active)", ":active", ":hover"):
        assert state in CSS
    assert "color:#f4f1ea !important" in CSS


def test_rank_is_zero_padded_and_never_wraps():
    nine = row_content_html(9, "turismo", "f", "x", [])
    ten = row_content_html(10, "turismo", "f", "x", [])
    hundred = row_content_html(100, "turismo", "f", "x", [])

    assert '<div class="rank">09</div>' in nine
    assert '<div class="rank">10</div>' in ten
    assert '<div class="rank">100</div>' in hundred
    assert "white-space:nowrap" in CSS.split("\n.rank{")[1].split("}")[0]
