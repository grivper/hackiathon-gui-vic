"""Tests for the chat "contradiccion" response type (odd/tasks/chat-contradiccion.md, C1).

Covers: listing every cited version, the pending-review notice, citation union,
the <2-cited-claims fallback, and that respuesta/abstencion fichas are unchanged.
Also validates the shape of the synthetic fichas fixture (C3) used by the benchmark
runner, never by the real app default path.
"""
from __future__ import annotations

import json
from pathlib import Path

from unittest.mock import MagicMock, Mock

import duckdb
import pytest

from app.app import render_group_chat
from app.data import DEFAULT_FICHAS_PATH, ChatResponse, InboxGroup, ask_group_question

SYNTHETIC_FICHAS_PATH = Path("data/fichas_sinteticas.jsonl")
SYNTHETIC_GROUP_IDS = (
    "SYN-ECON-CONTRADICTION",
    "SYN-LOG-CONTRADICTION",
    "SYN-TUR-CONTRADICTION",
    "SYN-SERV-CONTRADICTION",
    "SYN-NAT-CONTRADICTION",
    "SYN-REG-CONTRADICTION",
)


def _create_empty_motor(tmp_path):
    """A motor DuckDB with the fichas table but no rows, so every lookup falls back
    to the JSONL fixture the test writes."""

    motor_path = tmp_path / "motor.duckdb"
    connection = duckdb.connect(str(motor_path))
    try:
        connection.execute(
            "CREATE TABLE fichas (id_caso TEXT, estado_revision TEXT, "
            "tipo_respuesta TEXT, ficha TEXT, generado_en TIMESTAMP)"
        )
    finally:
        connection.close()
    return motor_path


def _write_jsonl(tmp_path, *payloads):
    fichas_path = tmp_path / "fichas.jsonl"
    fichas_path.write_text(
        "".join(json.dumps(payload) + "\n" for payload in payloads), encoding="utf-8"
    )
    return fichas_path


def _contradiction_payload(group_id="G-CONTRA", *, claim_count=2):
    claims_source = [
        ("Fuente sintética A: la inflación subió.", "N-a"),
        ("Fuente sintética B: la inflación bajó.", "N-b"),
        ("Fuente sintética C: sin citación todavía.", None),
    ]
    afirmaciones = []
    citas = []
    for texto, id_evidencia in claims_source[:claim_count]:
        if id_evidencia is not None:
            afirmaciones.append(
                {"texto": texto, "id_evidencia": id_evidencia, "campo": "titulo"}
            )
            citas.append({"id_evidencia": id_evidencia, "campo": "titulo"})
        else:
            afirmaciones.append({"texto": texto, "campo": "titulo"})
    return {
        "id_caso": group_id,
        "estado_revision": "nuevo",
        "tipo_respuesta": "contradiccion",
        "borrador": "borrador cualquiera",
        "citas": citas,
        "afirmaciones": afirmaciones,
        "motivo_abstencion": None,
    }


def _respuesta_payload(group_id="G-REAL"):
    return {
        "id_caso": group_id,
        "estado_revision": "nuevo",
        "tipo_respuesta": "respuesta",
        "borrador": "La inflación cayó en junio.",
        "citas": [{"id_evidencia": "N-real", "campo": "titulo"}],
        "afirmaciones": [
            {"texto": "La inflación cayó en junio.", "id_evidencia": "N-real", "campo": "titulo"}
        ],
        "motivo_abstencion": None,
    }


# --------------------------------------------------------------------------- C1: contradiccion type

def test_contradiction_lists_every_cited_version_and_pending_review(tmp_path):
    motor_path = _create_empty_motor(tmp_path)
    fichas_path = _write_jsonl(tmp_path, _contradiction_payload())

    response = ask_group_question(
        "G-CONTRA", "¿Qué pasó con la inflación?", motor_path=motor_path, fichas_path=fichas_path
    )

    assert response.contradiccion is True
    assert response.abstencion is False
    assert "- Fuente sintética A: la inflación subió. [N-a]" in response.respuesta
    assert "- Fuente sintética B: la inflación bajó. [N-b]" in response.respuesta
    assert "Revisión pendiente" in response.respuesta
    assert response.citas == ["N-a", "N-b"]


def test_contradiction_never_picks_a_winner(tmp_path):
    motor_path = _create_empty_motor(tmp_path)
    fichas_path = _write_jsonl(tmp_path, _contradiction_payload())

    response = ask_group_question(
        "G-CONTRA", "¿cuál es la verdadera?", motor_path=motor_path, fichas_path=fichas_path
    )

    lowered = response.respuesta.lower()
    for forbidden in ("verdadera es", "versión correcta es", "ganadora", "gana la versión"):
        assert forbidden not in lowered


def test_contradiction_applies_to_any_question_on_the_group(tmp_path):
    """A contradictory group answers by exposing the disagreement regardless of the
    specific question asked (no term matching gate on the contradiccion branch)."""

    motor_path = _create_empty_motor(tmp_path)
    fichas_path = _write_jsonl(tmp_path, _contradiction_payload())

    response = ask_group_question(
        "G-CONTRA", "pregunta totalmente sin relación con los términos", motor_path=motor_path, fichas_path=fichas_path
    )

    assert response.contradiccion is True
    assert response.citas == ["N-a", "N-b"]


def test_contradiction_with_fewer_than_two_cited_claims_falls_back(tmp_path):
    motor_path = _create_empty_motor(tmp_path)
    fichas_path = _write_jsonl(tmp_path, _contradiction_payload(claim_count=1))

    response = ask_group_question(
        "G-CONTRA", "¿Qué pasó con la inflación?", motor_path=motor_path, fichas_path=fichas_path
    )

    assert response.contradiccion is False
    assert response == ChatResponse("Fuente sintética A: la inflación subió.", False, ["N-a"])


def test_non_contradiction_fichas_are_unchanged(tmp_path):
    motor_path = _create_empty_motor(tmp_path)
    fichas_path = _write_jsonl(tmp_path, _respuesta_payload())

    response = ask_group_question(
        "G-REAL", "¿Qué pasó con la inflación?", motor_path=motor_path, fichas_path=fichas_path
    )

    assert response == ChatResponse("La inflación cayó en junio.", False, ["N-real"])
    assert response.contradiccion is False


def test_default_fichas_path_is_the_real_path_not_synthetic():
    assert DEFAULT_FICHAS_PATH == Path("data/fichas.jsonl")


# --------------------------------------------------------------------------- C2: chat UI warning

_UI_GROUP = InboxGroup(
    grupo_id="G-1",
    titulo_representativo="",
    n_noticias=1,
    n_procedencias=1,
    fecha_max=None,
    corroboracion=1,
    es_repeticion=False,
    tema="otros",
    R=0, I=0, U=0, N=0, E=0, puntaje=0, prioridad="bajo",
    estado_evidencia="insuficiente", version_reglas="v0.3",
    motivos="", contexto_oficial=None, evento_usgs_id=None,
)


def test_render_group_chat_shows_contradiction_warning(monkeypatch):
    widgets = {name: Mock() for name in ("caption", "warning", "markdown")}
    monkeypatch.setattr("app.app.st.expander", MagicMock())
    monkeypatch.setattr("app.app.st.chat_input", Mock(return_value="¿cuál es la verdadera?"))
    monkeypatch.setattr("app.app.st.chat_message", MagicMock())
    monkeypatch.setattr("app.app.st.spinner", MagicMock())
    monkeypatch.setattr("app.app.st.session_state", {})
    for name, mock in widgets.items():
        monkeypatch.setattr(f"app.app.st.{name}", mock)
    monkeypatch.setattr(
        "app.app.ask_group_question",
        Mock(return_value=ChatResponse("- versión A [N-a]\n- versión B [N-b]", False, ["N-a", "N-b"], True)),
    )

    render_group_chat(_UI_GROUP)

    assert any("contradicción" in str(call).lower() for call in widgets["warning"].call_args_list)
    widgets["caption"].assert_any_call("Citas verificadas: N-a, N-b")


# --------------------------------------------------------------------------- C3: synthetic fixture shape

def _load_synthetic_fichas():
    lines = SYNTHETIC_FICHAS_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_synthetic_fichas_file_has_six_records_matching_benchmark_group_ids():
    records = _load_synthetic_fichas()
    assert len(records) == 6
    assert {record["id_caso"] for record in records} == set(SYNTHETIC_GROUP_IDS)


@pytest.mark.parametrize("group_id", SYNTHETIC_GROUP_IDS)
def test_synthetic_ficha_has_two_cited_contradictory_claims(group_id):
    records = {record["id_caso"]: record for record in _load_synthetic_fichas()}
    record = records[group_id]

    assert record["tipo_respuesta"] == "contradiccion"
    assert record.get("sintetico") is True

    cited_evidence_ids = {cita["id_evidencia"] for cita in record["citas"]}
    assert len(cited_evidence_ids) == 2

    claims_with_citations = [
        claim for claim in record["afirmaciones"] if claim.get("id_evidencia") in cited_evidence_ids
    ]
    assert len(claims_with_citations) == 2

    expected_prefix = group_id.removesuffix("-CONTRADICTION").replace("SYN-", "SYN-")
    assert cited_evidence_ids == {f"{expected_prefix}-V1", f"{expected_prefix}-V2"}


def test_synthetic_fichas_never_in_real_fichas_file():
    real_lines = Path("data/fichas.jsonl").read_text(encoding="utf-8").splitlines()
    real_ids = {json.loads(line)["id_caso"] for line in real_lines if line.strip()}
    assert real_ids.isdisjoint(SYNTHETIC_GROUP_IDS)
