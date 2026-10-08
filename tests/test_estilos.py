from __future__ import annotations

from app.estilos import (
    CSS,
    component_bars_html,
    empty_draft_html,
    evidence_head_html,
    evidence_kv_html,
    hero_html,
    info_html,
    score_card_html,
)


def test_hero_escapes_nothing_dynamic_but_shows_the_three_kpis():
    html_out = hero_html(12, 3, 7)

    assert "Inteligencia editorial" in html_out
    assert ">12<" in html_out and ">3<" in html_out and ">7<" in html_out
    for label in ("Registros priorizados", "Prioridad alta", "Requieren evidencia"):
        assert label in html_out


def test_score_card_escapes_dynamic_text():
    html_out = score_card_html(
        rank=1,
        tema="<b>tema</b>",
        fecha="01/01/2026",
        titulo="<script>alert(1)</script>",
        chips=[("Evidencia <i>x</i>", "warn")],
        puntaje=55.0,
    )

    assert "<script>" not in html_out
    assert "&lt;script&gt;" in html_out
    assert "<b>tema</b>" not in html_out
    assert "&lt;i&gt;" in html_out
    assert "chip warn" in html_out


def test_score_bar_width_is_clamped_to_0_100():
    assert "width:100%" in score_card_html(1, "t", "f", "x", [], 250.0)
    assert "width:0%" in score_card_html(1, "t", "f", "x", [], -5.0)


def test_component_bars_render_all_five_with_value_and_clamp():
    html_out = component_bars_html({"R": 30.0, "I": 0.0, "U": 150.0, "N": 10.0, "E": 0.0})

    for letter in "RIUNE":
        assert f"<b>{letter}</b>" in html_out
    assert "width:100%" in html_out
    assert "30.0" in html_out


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

    assert out == '<div class="info"><div>Por verificar: algo</div></div>'


def test_empty_draft_html_keeps_the_exact_message():
    out = empty_draft_html()

    assert 'class="empty"' in out
    assert "Borrador no generado para este grupo (ejecutar <code>make generar</code>)." in out


def test_evidence_head_escapes_title_and_id():
    out = evidence_head_html("<script>x</script>", "N-1<")

    assert "<script>" not in out
    assert "ID de evidencia: N-1&lt;" in out


def test_evidence_kv_marks_missing_values_and_escapes():
    out = evidence_kv_html([("Medio", "<b>TVN</b>"), ("Fecha", "No disponible")])

    assert "&lt;b&gt;TVN&lt;/b&gt;" in out
    assert out.count('class="v na"') == 1


def test_css_styles_expanders_chat_and_empty_states():
    for selector in ('stExpander', 'stChatInput', 'stChatMessage', ".kv", ".empty", ".info"):
        assert selector in CSS
