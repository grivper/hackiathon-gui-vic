"""Tests de motor/evaluar_benchmark.py (TAR-011, B1; extendido por
odd/tasks/chat-contradiccion.md, C4): corredor del benchmark de desarrollo contra
`app.data.ask_group_question`, con una `ask` falsa inyectada para no depender de
Ollama ni de bases DuckDB reales."""
from __future__ import annotations

from dataclasses import dataclass

from motor import evaluar_benchmark as eb


@dataclass(frozen=True)
class FakeResponse:
    respuesta: str
    abstencion: bool
    citas: list[str]
    contradiccion: bool = False


def _record(**overrides):
    base = {
        "id": "TAR023-001",
        "case": "supported",
        "question": "pregunta",
        "target_group_id": "G-1",
        "expected_response_type": "respuesta",
        "required_evidence_ids": [],
        "forbidden_claims": [],
        "snapshot_manifest_sha256": "abc123",
    }
    base.update(overrides)
    return base


def make_fake_ask(responses: dict[str, FakeResponse]):
    """responses keyed by record id; the fake ignores grupo_id/question and
    looks the canned response up by a sentinel the test stashes on question."""

    def fake_ask(grupo_id, question, *, motor_path=None, signals_path=None, fichas_path=None):
        return responses[question]

    return fake_ask


# --------------------------------------------------------------------------- scoring: respuesta

def test_respuesta_ok_full_recall():
    record = _record(required_evidence_ids=["N-1", "N-2"])
    response = FakeResponse("afirmacion citada", False, ["N-1", "N-2", "N-3"])
    result = eb.score_record(record, response)
    assert result["observed_response_type"] == "respuesta"
    assert result["type_ok"] is True
    assert result["required_evidence_recall"] == 1.0
    assert result["abstention_clean"] is None


def test_respuesta_ok_partial_recall():
    record = _record(required_evidence_ids=["N-1", "N-2"])
    response = FakeResponse("afirmacion citada", False, ["N-1"])
    result = eb.score_record(record, response)
    assert result["type_ok"] is True
    assert result["required_evidence_recall"] == 0.5


def test_respuesta_expected_but_abstained_is_not_type_ok():
    record = _record(required_evidence_ids=["N-1"])
    response = FakeResponse(eb.ABSTENTION_MESSAGE, True, [])
    result = eb.score_record(record, response)
    assert result["observed_response_type"] == "abstencion"
    assert result["type_ok"] is False
    # el motor nunca cita evidencia al abstenerse: no hay evidencia que contar
    assert result["required_evidence_recall"] == 0.0


def test_respuesta_without_required_evidence_has_no_recall():
    record = _record(required_evidence_ids=[])
    response = FakeResponse("afirmacion citada", False, [])
    result = eb.score_record(record, response)
    assert result["required_evidence_recall"] is None


# --------------------------------------------------------------------------- scoring: abstencion

def test_abstencion_clean_when_expected_and_no_citas():
    record = _record(expected_response_type="abstencion", case="abstention", required_evidence_ids=[])
    response = FakeResponse(eb.ABSTENTION_MESSAGE, True, [])
    result = eb.score_record(record, response)
    assert result["observed_response_type"] == "abstencion"
    assert result["type_ok"] is True
    assert result["abstention_clean"] is True


def test_abstencion_dirty_when_citas_present():
    record = _record(expected_response_type="abstencion", case="abstention", required_evidence_ids=[])
    response = FakeResponse(eb.ABSTENTION_MESSAGE, True, ["N-1"])
    result = eb.score_record(record, response)
    assert result["abstention_clean"] is False


# --------------------------------------------------------------------------- scoring: contradiccion

def test_contradiccion_observed_when_response_marks_contradiccion():
    record = _record(
        expected_response_type="contradiccion", case="contradiction",
        required_evidence_ids=["SYN-ECON-V1", "SYN-ECON-V2"],
    )
    response = FakeResponse(
        "- versión A [SYN-ECON-V1]\n- versión B [SYN-ECON-V2]\nRevisión pendiente...",
        False, ["SYN-ECON-V1", "SYN-ECON-V2"], True,
    )
    result = eb.score_record(record, response)
    assert result["observed_response_type"] == "contradiccion"
    assert result["type_ok"] is True
    assert result["required_evidence_recall"] == 1.0
    # una respuesta con contradiccion no es una abstención: no aplica abstention_clean
    assert result["abstention_clean"] is None


def test_contradiccion_expected_but_chat_answered_or_abstained_is_not_type_ok():
    record = _record(expected_response_type="contradiccion", case="contradiction", required_evidence_ids=[])
    for response in (FakeResponse("algo", False, ["N-1"]), FakeResponse(eb.ABSTENTION_MESSAGE, True, [])):
        result = eb.score_record(record, response)
        assert result["type_ok"] is False


def test_contradiccion_partial_evidence_recall():
    record = _record(
        expected_response_type="contradiccion", case="contradiction",
        required_evidence_ids=["SYN-ECON-V1", "SYN-ECON-V2"],
    )
    response = FakeResponse("solo una versión citada", False, ["SYN-ECON-V1"], True)
    result = eb.score_record(record, response)
    assert result["observed_response_type"] == "contradiccion"
    assert result["type_ok"] is True
    assert result["required_evidence_recall"] == 0.5


def test_unexpected_contradiccion_is_not_type_ok():
    """Si el chat marca contradiccion pero el registro esperaba otra cosa, no es
    type_ok (ya no existe un bucket aparte para 'contradiccion no soportada')."""
    record = _record(expected_response_type="respuesta", case="supported", required_evidence_ids=["N-1"])
    response = FakeResponse("- v1 [N-1]\n- v2 [N-2]\nRevisión pendiente...", False, ["N-1", "N-2"], True)
    result = eb.score_record(record, response)
    assert result["observed_response_type"] == "contradiccion"
    assert result["type_ok"] is False


# --------------------------------------------------------------------------- summarize

def test_summarize_counts_and_rates():
    records = [
        _record(id="A", expected_response_type="respuesta", case="supported", required_evidence_ids=["N-1"]),
        _record(id="B", expected_response_type="respuesta", case="supported", required_evidence_ids=["N-1", "N-2"]),
        _record(id="C", expected_response_type="abstencion", case="abstention", required_evidence_ids=[]),
        _record(
            id="D", expected_response_type="contradiccion", case="contradiction",
            required_evidence_ids=["SYN-X-V1", "SYN-X-V2"],
        ),
    ]
    responses = {
        "A": FakeResponse("x", False, ["N-1"]),  # ok, recall 1.0
        "B": FakeResponse("x", False, ["N-1"]),  # ok, recall 0.5
        "C": FakeResponse(eb.ABSTENTION_MESSAGE, True, []),  # ok, clean
        "D": FakeResponse("x", False, ["SYN-X-V1", "SYN-X-V2"], True),  # ok, recall 1.0
    }
    results = [eb.score_record(r, responses[r["id"]]) for r in records]
    summary = eb.summarize(records, results)

    assert summary["total"] == 4
    assert summary["overall_type_ok_rate"] == 1.0  # A, B, C, D all ok
    assert summary["mean_recall_respuesta"] == 0.75  # (1.0 + 0.5) / 2
    assert summary["mean_recall_contradiccion"] == 1.0
    assert summary["abstention_clean_rate"] == 1.0
    assert summary["failing_ids"] == []

    by_expected = summary["by_expected_response_type"]
    assert by_expected["respuesta"]["count"] == 2
    assert by_expected["respuesta"]["type_ok_rate"] == 1.0
    assert by_expected["contradiccion"]["count"] == 1
    assert by_expected["contradiccion"]["type_ok_rate"] == 1.0

    by_case = summary["by_case"]
    assert by_case["supported"]["count"] == 2
    assert by_case["contradiction"]["count"] == 1


# --------------------------------------------------------------------------- evaluate_records (I/O boundary)

def test_evaluate_records_uses_injected_ask():
    records = [
        _record(id="A", question="q-a", required_evidence_ids=["N-1"]),
        _record(id="B", expected_response_type="abstencion", case="abstention", question="q-b", required_evidence_ids=[]),
    ]
    fake_ask = make_fake_ask({
        "q-a": FakeResponse("x", False, ["N-1"]),
        "q-b": FakeResponse(eb.ABSTENTION_MESSAGE, True, []),
    })
    results = eb.evaluate_records(
        records, ask=fake_ask, motor_path="m.duckdb", signals_path="s.duckdb", fichas_path="f.jsonl",
        fichas_sinteticas_path="fs.jsonl",
    )
    assert [r["id"] for r in results] == ["A", "B"]
    assert results[0]["type_ok"] is True
    assert results[1]["type_ok"] is True


def test_evaluate_records_routes_synthetic_records_to_synthetic_fichas_path():
    records = [
        _record(id="A", question="q-a", required_evidence_ids=[]),
        _record(
            id="D", question="q-d", expected_response_type="contradiccion", case="contradiction",
            required_evidence_ids=[], synthetic=True,
        ),
    ]
    seen_fichas_paths = []

    def fake_ask(grupo_id, question, *, motor_path=None, signals_path=None, fichas_path=None):
        seen_fichas_paths.append(fichas_path)
        return FakeResponse("x", False, [])

    eb.evaluate_records(
        records, ask=fake_ask, motor_path="m.duckdb", signals_path="s.duckdb",
        fichas_path="real.jsonl", fichas_sinteticas_path="sinteticas.jsonl",
    )

    assert seen_fichas_paths == ["real.jsonl", "sinteticas.jsonl"]


# --------------------------------------------------------------------------- report

def test_render_report_contains_manual_review_section_and_forbidden_claims():
    records = [
        _record(id="A", forbidden_claims=["afirmar algo prohibido"]),
    ]
    responses = {"A": FakeResponse("x", False, [])}
    results = [eb.score_record(r, responses[r["id"]]) for r in records]
    summary = eb.summarize(records, results)
    report = eb.render_report(records, results, summary, manifest_hash="abc123")

    assert "Revisión manual pendiente" in report
    assert "afirmar algo prohibido" in report
    assert "abc123" in report
    assert "determinista" in report.lower() or "extractiv" in report.lower()
    assert "TAR023-001" not in report or "A" in report  # id del registro aparece en alguna tabla
    assert "A" in report


def test_render_report_shows_contradiccion_recall_not_unsupported_count():
    records = [
        _record(
            id="D", expected_response_type="contradiccion", case="contradiction",
            required_evidence_ids=["SYN-X-V1", "SYN-X-V2"],
        ),
    ]
    responses = {"D": FakeResponse("x", False, ["SYN-X-V1", "SYN-X-V2"], True)}
    results = [eb.score_record(r, responses[r["id"]]) for r in records]
    summary = eb.summarize(records, results)
    report = eb.render_report(records, results, summary, manifest_hash="abc123")

    assert "sin soporte posible" not in report.lower()
    assert "recall" in report.lower() and "contradiccion" in report.lower()
    assert "100.0%" in report
