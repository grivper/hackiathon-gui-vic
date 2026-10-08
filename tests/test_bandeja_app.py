from __future__ import annotations

from datetime import date, datetime

from app.app import (
    database_fingerprint,
    editorial_guidance,
    evidence_date_label,
    evidence_verification_guidance,
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
