from __future__ import annotations

import json
from datetime import datetime

import duckdb
import pytest

from app.data import ask_group_question, fetch_group_ficha, persist_ficha_review_state


def _create_motor(tmp_path, rows=()):
    motor_path = tmp_path / "motor.duckdb"
    connection = duckdb.connect(str(motor_path))
    try:
        if rows is not None:
            connection.execute(  # noqa: S608 - static schema, no interpolated input
                "CREATE TABLE fichas (id_caso TEXT, estado_revision TEXT, "
                "tipo_respuesta TEXT, ficha TEXT, generado_en TIMESTAMP)"
            )
            if rows:
                connection.executemany("INSERT INTO fichas VALUES (?, ?, ?, ?, ?)", rows)
    finally:
        connection.close()
    return motor_path


def _payload(group_id="G-REAL"):
    return {
        "id_caso": group_id,
        "estado_revision": "nuevo",
        "tipo_respuesta": "respuesta",
        "borrador": "La inflación cayó en junio.",
        "citas": [{"id_evidencia": "N-real", "campo": "titulo"}],
        "afirmaciones": [
            {
                "texto": "La inflación cayó en junio.",
                "id_evidencia": "N-real",
                "campo": "titulo",
            }
        ],
        "motivo_abstencion": None,
    }


def _write_jsonl(tmp_path, *payloads):
    fichas_path = tmp_path / "fichas.jsonl"
    fichas_path.write_text(
        "".join(json.dumps(payload) + "\n" for payload in payloads), encoding="utf-8"
    )
    return fichas_path


def test_duckdb_ficha_is_authoritative_over_jsonl(tmp_path):
    duckdb_payload = _payload()
    duckdb_payload["borrador"] = "Ficha DuckDB."
    motor_path = _create_motor(
        tmp_path,
        [("G-REAL", "en revisión", "respuesta", json.dumps(duckdb_payload), datetime(2026, 1, 2))],
    )
    fichas_path = _write_jsonl(tmp_path, _payload())

    ficha = fetch_group_ficha(motor_path, tmp_path / "signals.duckdb", "G-REAL", fichas_path=fichas_path)

    assert ficha is not None
    assert ficha.borrador == "Ficha DuckDB."
    assert ficha.estado_revision == "en revisión"
    assert ficha.source == "duckdb"
    assert ficha.persistable is True
    assert persist_ficha_review_state(
        motor_path, "G-REAL", "aprobado como borrador", ficha=ficha
    ) is True
    updated = fetch_group_ficha(motor_path, tmp_path / "signals.duckdb", "G-REAL")
    assert updated is not None
    assert updated.estado_revision == "aprobado como borrador"


@pytest.mark.parametrize("rows", [None, ()], ids=["missing-table", "missing-row"])
def test_absent_duckdb_ficha_falls_back_to_matching_jsonl(tmp_path, rows):
    motor_path = _create_motor(tmp_path, rows)
    fichas_path = _write_jsonl(tmp_path, _payload())

    ficha = fetch_group_ficha(motor_path, tmp_path / "signals.duckdb", "G-REAL", fichas_path=fichas_path)

    assert ficha is not None
    assert ficha.source == "jsonl"
    assert ficha.persistable is False
    assert ficha.estado_revision == "nuevo"


@pytest.mark.parametrize("content", [None, "", "not json\n", '{"id_caso": "G-OTHER"}\n'])
def test_unavailable_jsonl_never_supplies_a_ficha(tmp_path, content):
    motor_path = _create_motor(tmp_path, None)
    fichas_path = tmp_path / "fichas.jsonl"
    if content is not None:
        fichas_path.write_text(content, encoding="utf-8")

    assert fetch_group_ficha(motor_path, tmp_path / "signals.duckdb", "G-REAL", fichas_path=fichas_path) is None


def test_persistence_is_gated_by_ficha_provenance(tmp_path):
    other_payload = _payload("G-DUCK")
    motor_path = _create_motor(
        tmp_path,
        [("G-DUCK", "nuevo", "respuesta", json.dumps(other_payload), datetime(2026, 1, 2))],
    )
    fallback = fetch_group_ficha(
        motor_path,
        tmp_path / "signals.duckdb",
        "G-REAL",
        fichas_path=_write_jsonl(tmp_path, _payload()),
    )
    assert fallback is not None

    assert persist_ficha_review_state(motor_path, "G-REAL", "aprobado como borrador", ficha=fallback) is False
    assert persist_ficha_review_state(motor_path, "G-REAL", "nuevo") is False


def test_supported_question_extracts_existing_claim_and_its_citation(tmp_path):
    motor_path = _create_motor(tmp_path, None)
    fichas_path = _write_jsonl(tmp_path, _payload())

    response = ask_group_question(
        "G-REAL",
        "¿Qué pasó con la inflación?",
        motor_path=motor_path,
        fichas_path=fichas_path,
    )

    assert response == type(response)("La inflación cayó en junio.", False, ["N-real"])


def test_unmatched_question_abstains_without_citations_or_fake_evidence(tmp_path):
    motor_path = _create_motor(tmp_path, None)
    fichas_path = _write_jsonl(tmp_path, _payload())

    response = ask_group_question(
        "G-REAL",
        "¿Quién ganó las elecciones?",
        motor_path=motor_path,
        fichas_path=fichas_path,
    )

    assert response.abstencion is True
    assert response.citas == []
    assert "E-" not in response.respuesta
