from __future__ import annotations

from datetime import date, datetime

from app.app import (
    database_fingerprint,
    editorial_guidance,
    evidence_date_label,
    evidence_verification_guidance,
    render_official_context,
)


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
    st_info.assert_any_call("**Evento sísmico verificado (USGS):** [usgs-123](https://earthquake.usgs.gov/earthquakes/eventpage/usgs-123)")
