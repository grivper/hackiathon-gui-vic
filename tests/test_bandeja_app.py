from __future__ import annotations

from datetime import date, datetime

from app.app import (
    database_fingerprint,
    editorial_guidance,
    evidence_date_label,
    evidence_verification_guidance,
    render_group_chat,
    render_official_context,
)
from app.data import InboxGroup


def test_database_fingerprint_changes_when_either_database_changes(tmp_path):
    motor_path = tmp_path / "motor.duckdb"
    signals_path = tmp_path / "senales.duckdb"
    motor_path.write_bytes(b"motor-v1")
    signals_path.write_bytes(b"signals-v1")

    original = database_fingerprint(motor_path, signals_path)

    motor_path.write_bytes(b"motor-v2-with-a-different-size")
    after_motor_change = database_fingerprint(motor_path, signals_path)
    signals_path.write_bytes(b"signals-v2-with-a-different-size")
    after_signals_change = database_fingerprint(motor_path, signals_path)

    assert after_motor_change != original
    assert after_signals_change != after_motor_change


def test_high_priority_with_insufficient_evidence_requires_investigation():
    guidance = editorial_guidance("alto", "insuficiente")

    assert "requiere investigación" in guidance
    assert "no es publicable" in guidance


def test_evidence_date_label_keeps_missing_publication_date_unavailable():
    assert evidence_date_label(None) == "No disponible"
    assert evidence_date_label(datetime(2026, 1, 3, 14, 30)) == "03/01/2026"
    assert evidence_date_label(date(2026, 1, 4)) == "04/01/2026"


def test_insufficient_evidence_verification_guidance_requires_investigation():
    guidance = evidence_verification_guidance("insuficiente")

    assert "procedencias distintas" in guidance
    assert "requiere investigación" in guidance
    assert "no es publicable" in guidance


def test_render_official_context_avoids_rendering_when_missing(monkeypatch):
    from unittest.mock import Mock
    st_info = Mock()
    st_markdown = Mock()
    monkeypatch.setattr("app.app.st.info", st_info)
    monkeypatch.setattr("app.app.st.markdown", st_markdown)
    render_official_context(None, None)
    render_official_context("", "")
    st_info.assert_not_called()
    st_markdown.assert_not_called()


def test_render_official_context_displays_available_sources(monkeypatch):
    from unittest.mock import Mock

    st_info = Mock()
    st_markdown = Mock()
    monkeypatch.setattr("app.app.st.info", st_info)
    monkeypatch.setattr("app.app.st.markdown", st_markdown)
    render_official_context("PIB: 5%", "usgs-123")
    st_markdown.assert_any_call("**Contexto oficial (Banco Mundial / USGS)**")
    st_info.assert_any_call("**Indicadores Banco Mundial:** PIB: 5%")
    st_info.assert_any_call(
        "**Evento sísmico verificado (USGS):** [usgs-123](https://earthquake.usgs.gov/earthquakes/eventpage/usgs-123)"
    )


def test_render_group_chat_initializes_empty_session_state_and_renders_input(monkeypatch):
    from unittest.mock import MagicMock, Mock

    st_expander = MagicMock()
    st_caption = Mock()
    st_chat_input = Mock(return_value=None)
    session_state = {}

    monkeypatch.setattr("app.app.st.expander", st_expander)
    monkeypatch.setattr("app.app.st.caption", st_caption)
    monkeypatch.setattr("app.app.st.chat_input", st_chat_input)
    monkeypatch.setattr("app.app.st.session_state", session_state)

    group = InboxGroup(
        grupo_id="G-1",
        titulo_representativo="",
        n_noticias=1,
        n_procedencias=1,
        fecha_max=date(2026, 1, 1),
        corroboracion=1,
        es_repeticion=False,
        tema="otros",
        R=0, I=0, U=0, N=0, E=0, puntaje=0, prioridad="bajo",
        estado_evidencia="insuficiente", version_reglas="v0.3",
        motivos="", contexto_oficial=None, evento_usgs_id=None
    )

    render_group_chat(group)

    assert "chat_G-1" in session_state
    assert session_state["chat_G-1"] == []
    st_chat_input.assert_called_once()
