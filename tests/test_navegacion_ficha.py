from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).parents[1] / "app"
MOTOR = Path(__file__).parents[1] / "data" / "motor.duckdb"

pytestmark = pytest.mark.skipif(not MOTOR.exists(), reason="requires the local motor database")


def _app(monkeypatch) -> AppTest:
    monkeypatch.syspath_prepend(str(APP_DIR))
    # Script mode loads the sibling modules as top-level names.
    for name in ("data", "estilos"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    return AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=120).run()


def _text(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def test_bandeja_lists_rows_with_open_buttons_and_no_ficha_sections(monkeypatch):
    at = _app(monkeypatch)

    assert not at.exception
    assert any(b.key and b.key.startswith("abrir_") for b in at.button)
    assert "Bandeja de revisión" in _text(at)
    assert "Resumen del reporte" not in _text(at)


def test_open_ficha_then_back_restores_the_bandeja(monkeypatch):
    at = _app(monkeypatch)
    first = next(b for b in at.button if b.key and b.key.startswith("abrir_"))
    group_id = first.key.removeprefix("abrir_")

    first.click().run()

    assert not at.exception
    text = _text(at)
    assert at.session_state["ficha_id"] == group_id
    assert f"Registro editorial {group_id}" in text
    for section in ("Resumen del reporte", "Evidencia y procedencias", "Puntaje de atención"):
        assert section in text
    assert "Bandeja de revisión" not in text

    next(b for b in at.button if b.key == "volver-abajo").click().run()

    assert not at.exception
    assert at.session_state["ficha_id"] is None
    assert any(b.key and b.key.startswith("abrir_") for b in at.button)
