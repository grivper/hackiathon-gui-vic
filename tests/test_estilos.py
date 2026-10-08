from __future__ import annotations

from app.estilos import CSS, component_bars_html, hero_html, score_card_html


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
