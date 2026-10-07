"""Tests de motor/llm.py (TAR-009, G5): clientes del LLM local.

Sin Ollama real: un servidor HTTP de juguete hace de Ollama y registra lo que recibe. Un
fallo del modelo (red, timeout, JSON roto) nunca lanza: devuelve una Respuesta con `error`
y sin contenido, y el pipeline lo convierte en abstención.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from motor import llm

ESQUEMA = {"type": "object", "properties": {"x": {"type": "string"}}}


@pytest.fixture()
def servidor():
    estado = {"recibido": None, "respuesta": None, "status": 200}

    class Manejador(BaseHTTPRequestHandler):
        def do_POST(self):
            largo = int(self.headers["Content-Length"])
            estado["recibido"] = json.loads(self.rfile.read(largo))
            self.send_response(estado["status"])
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(estado["respuesta"]).encode())

        def log_message(self, *args):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Manejador)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    estado["host"] = f"http://127.0.0.1:{srv.server_port}"
    yield estado
    srv.shutdown()


def _ok(contenido: str) -> dict:
    return {"message": {"content": contenido}, "prompt_eval_count": 120, "eval_count": 40,
            "eval_duration": 4_000_000_000, "load_duration": 1_000_000_000}


def test_ollama_envia_modelo_mensajes_esquema_y_opciones_deterministas(servidor):
    servidor["respuesta"] = _ok('{"x": "hola"}')
    cliente = llm.ClienteOllama("qwen-test", host=servidor["host"])
    r = cliente.generar("SISTEMA", "USUARIO", ESQUEMA)
    body = servidor["recibido"]
    assert body["model"] == "qwen-test" and body["stream"] is False
    assert body["format"] == ESQUEMA
    assert body["messages"] == [{"role": "system", "content": "SISTEMA"}, {"role": "user", "content": "USUARIO"}]
    assert body["options"] == {"num_thread": 4, "num_ctx": 4096, "num_predict": 768, "temperature": 0, "seed": 7}
    assert r.error is None and r.contenido == {"x": "hola"}


def test_ollama_registra_modelo_parametros_y_metricas(servidor):
    servidor["respuesta"] = _ok('{"x": "hola"}')
    r = llm.ClienteOllama("qwen-test", host=servidor["host"], num_thread=2).generar("s", "u", ESQUEMA)
    assert r.modelo == "qwen-test" and r.opciones["num_thread"] == 2
    assert r.tokens_prompt == 120 and r.tokens_salida == 40
    assert r.tokens_por_segundo == pytest.approx(10.0)
    assert r.duracion_s >= 0


def test_json_roto_devuelve_error_sin_lanzar(servidor):
    servidor["respuesta"] = _ok("esto no es json")
    r = llm.ClienteOllama("m", host=servidor["host"]).generar("s", "u", ESQUEMA)
    assert r.contenido is None and r.error == "json_invalido" and r.texto == "esto no es json"


def test_http_error_devuelve_error_sin_lanzar(servidor):
    servidor["status"] = 500
    servidor["respuesta"] = {"error": "boom"}
    r = llm.ClienteOllama("m", host=servidor["host"]).generar("s", "u", ESQUEMA)
    assert r.contenido is None and r.error.startswith("http_")


def test_servidor_caido_devuelve_error_sin_lanzar():
    r = llm.ClienteOllama("m", host="http://127.0.0.1:9", timeout=2).generar("s", "u", ESQUEMA)
    assert r.contenido is None and r.error.startswith("conexion")


def test_cliente_falso_devuelve_en_orden_y_registra_llamadas():
    falso = llm.ClienteFalso([{"a": 1}, '{"b": 2}'])
    assert falso.generar("s1", "u1", ESQUEMA).contenido == {"a": 1}
    assert falso.generar("s2", "u2", ESQUEMA).contenido == {"b": 2}
    assert falso.llamadas == [("s1", "u1", ESQUEMA), ("s2", "u2", ESQUEMA)]
    assert falso.generar("s3", "u3", ESQUEMA).error == "sin_respuestas_configuradas"


def test_cliente_falso_puede_simular_fallo():
    r = llm.ClienteFalso([llm.Respuesta(error="conexion")]).generar("s", "u", ESQUEMA)
    assert r.contenido is None and r.error == "conexion"


def test_cliente_desde_entorno(monkeypatch):
    monkeypatch.setenv("LLM_MODELO", "mi-modelo")
    monkeypatch.setenv("OLLAMA_HOST", "http://otro:1234")
    monkeypatch.setenv("LLM_NUM_THREAD", "6")
    c = llm.cliente_desde_entorno()
    assert c.modelo == "mi-modelo" and c.host == "http://otro:1234" and c.opciones["num_thread"] == 6


# --------------------------------------------------------------------------- medición

def test_medir_reporta_mediana_p95_y_validez_de_citas():
    from motor import medir_llm

    paquete = {"grupo_id": "G", "tema": "economia", "items": [
        {"id_evidencia": "N-a", "tipo": "noticia", "campos": {"titulo": "Inflación cae 0,3 %"}}]}
    buena = {"tipo_respuesta": "respuesta", "versiones": [], "vacios": [], "alcance": "x",
             "afirmaciones": [{"texto": "Cae 0,3 %", "tipo": "hecho", "id_evidencia": "N-a", "campo": "titulo"}]}
    mala = {**buena, "afirmaciones": [{"texto": "Cae 9 %", "tipo": "hecho", "id_evidencia": "N-a", "campo": "titulo"}]}
    tiempos = iter([2.0, 4.0, 10.0])
    respuestas = [llm.Respuesta(contenido=c, modelo="m", duracion_s=next(tiempos), tokens_salida=50, tokens_por_segundo=10.0)
                  for c in (buena, buena, mala)]
    res = medir_llm.medir(llm.ClienteFalso(respuestas), [paquete] * 3)
    assert res["n"] == 3 and res["modelo"] == "m"
    assert res["tiempo_mediana_s"] == 4.0 and res["tiempo_p95_s"] == pytest.approx(9.4)
    assert res["salidas_validas"] == 3  # JSON con esquema correcto
    assert res["con_cita_valida"] == 2  # la tercera pierde su única afirmación (cifra inventada)
    assert res["tokens_por_segundo_mediana"] == 10.0
