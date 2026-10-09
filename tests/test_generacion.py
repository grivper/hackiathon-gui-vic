"""On-demand generation of one ficha from the UI (TAR-009 on top of motor.generar).

Uses ClienteFalso, so Ollama is not needed. The point of these tests is what the button
must NOT do: rewrite other fichas, overwrite a human review, or persist a transient
model failure.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import duckdb
import pytest
from test_generar import REGLAS, _a, _salida, dbs  # noqa: F401  (dbs is a fixture)

from app import generacion
from motor import generar, llm

REGLAS_YAML = Path(__file__).parents[1] / "motor" / "reglas_puntaje.yaml"


def _ficha(id_caso, estado="nuevo", extra=None):
    return {"id_caso": id_caso, "estado_revision": estado, "tipo_respuesta": "respuesta",
            "afirmaciones": [], "borrador": f"borrador {id_caso}", **(extra or {})}


def _lines(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# --------------------------------------------------------------------------- guardar_ficha

def test_guardar_ficha_keeps_every_other_line_of_the_jsonl_even_if_the_table_lacks_them(tmp_path):
    motor, jsonl = tmp_path / "motor.duckdb", tmp_path / "fichas.jsonl"
    # the committed jsonl has fichas this local database has never seen
    jsonl.write_text(
        "".join(json.dumps(_ficha(i)) + "\n" for i in ("G-1", "G-2", "G-3")), encoding="utf-8"
    )

    generar.guardar_ficha(motor, _ficha("G-9"), jsonl)

    assert [f["id_caso"] for f in _lines(jsonl)] == ["G-1", "G-2", "G-3", "G-9"]
    con = duckdb.connect(str(motor), read_only=True)
    try:
        assert con.execute("SELECT id_caso FROM fichas").fetchall() == [("G-9",)]
    finally:
        con.close()


def test_guardar_ficha_replaces_only_the_same_id(tmp_path):
    motor, jsonl = tmp_path / "motor.duckdb", tmp_path / "fichas.jsonl"
    jsonl.write_text(
        "".join(json.dumps(_ficha(i)) + "\n" for i in ("G-1", "G-2")), encoding="utf-8"
    )

    generar.guardar_ficha(motor, _ficha("G-2", extra={"borrador": "nuevo texto"}), jsonl)

    by_id = {f["id_caso"]: f for f in _lines(jsonl)}
    assert by_id["G-2"]["borrador"] == "nuevo texto"
    assert by_id["G-1"]["borrador"] == "borrador G-1"
    assert len(by_id) == 2


def test_guardar_ficha_creates_the_jsonl_when_it_does_not_exist(tmp_path):
    jsonl = tmp_path / "sub" / "fichas.jsonl"

    generar.guardar_ficha(tmp_path / "motor.duckdb", _ficha("G-1"), jsonl)

    assert [f["id_caso"] for f in _lines(jsonl)] == ["G-1"]


# --------------------------------------------------------------------------- generar_borrador

def test_generar_borrador_saves_only_that_group(dbs, tmp_path):  # noqa: F811
    motor, senales = dbs
    jsonl = tmp_path / "fichas.jsonl"
    jsonl.write_text(json.dumps(_ficha("G-OTRA")) + "\n", encoding="utf-8")
    cliente = llm.ClienteFalso([_salida(_a("Según tvn-pa.com, la inflación cayó 0,3 % en junio."))])

    result = generacion.generar_borrador(
        "G-ECO", motor, senales, jsonl, reglas_path=REGLAS_YAML, cliente=cliente
    )

    assert result.status == "generada"
    assert result.ficha["id_caso"] == "G-ECO" and "inflación cayó" in result.ficha["borrador"]
    assert [f["id_caso"] for f in _lines(jsonl)] == ["G-ECO", "G-OTRA"]


def test_generar_borrador_refuses_to_overwrite_a_human_review(dbs, tmp_path):  # noqa: F811
    motor, senales = dbs
    jsonl = tmp_path / "fichas.jsonl"
    generar.guardar_ficha(motor, _ficha("G-ECO", estado="aprobado como borrador"), jsonl)
    cliente = llm.ClienteFalso([_salida(_a("x"))])

    result = generacion.generar_borrador(
        "G-ECO", motor, senales, jsonl, reglas_path=REGLAS_YAML, cliente=cliente
    )

    assert result.status == "ya_revisada"
    assert cliente.llamadas == []  # the model is not even called
    assert _lines(jsonl)[0]["estado_revision"] == "aprobado como borrador"


def test_generar_borrador_does_not_persist_a_transient_model_failure(dbs, tmp_path):  # noqa: F811
    motor, senales = dbs
    jsonl = tmp_path / "fichas.jsonl"
    cliente = llm.ClienteFalso([llm.Respuesta(error="conexion", modelo="m")])

    result = generacion.generar_borrador(
        "G-ECO", motor, senales, jsonl, reglas_path=REGLAS_YAML, cliente=cliente
    )

    assert result.status == "error_modelo"
    assert not jsonl.exists()  # nothing written, so the user can simply retry


def test_a_legitimate_abstention_is_saved(dbs, tmp_path):  # noqa: F811
    motor, senales = dbs
    jsonl = tmp_path / "fichas.jsonl"

    result = generacion.generar_borrador(
        "G-VACIO", motor, senales, jsonl, reglas_path=REGLAS_YAML,
        cliente=llm.ClienteFalso([]),
    )

    assert result.status == "generada"
    assert result.ficha["tipo_respuesta"] == "abstencion"
    assert _lines(jsonl)[0]["motivo_abstencion"] == "sin_evidencia"


# --------------------------------------------------------------------------- estado_ollama

class _Handler(BaseHTTPRequestHandler):
    models = ["gemma3:4b"]

    def do_GET(self):
        body = json.dumps({"models": [{"name": m} for m in self.models]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture()
def fake_ollama():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_estado_ollama_ok_when_the_server_has_the_model(fake_ollama):
    ok, reason = generacion.estado_ollama(host=fake_ollama, modelo="gemma3:4b")
    assert ok and reason == ""


def test_estado_ollama_explains_a_missing_model(fake_ollama):
    ok, reason = generacion.estado_ollama(host=fake_ollama, modelo="otro:7b")
    assert not ok and "otro:7b" in reason


def test_estado_ollama_explains_an_unreachable_server():
    ok, reason = generacion.estado_ollama(host="http://127.0.0.1:9", modelo="gemma3:4b", timeout=0.5)
    assert not ok and "Ollama" in reason
