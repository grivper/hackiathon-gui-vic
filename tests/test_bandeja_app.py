from __future__ import annotations

from app.app import database_fingerprint, editorial_guidance


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
