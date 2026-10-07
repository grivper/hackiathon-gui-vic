"""Clientes del LLM local (TAR-009, G5).

`ClienteOllama` habla con Ollama por HTTP (solo biblioteca estándar, sin API externa) con
salida JSON restringida por esquema y opciones deterministas (temperatura 0, seed fija).
Cada `Respuesta` registra modelo, opciones, tokens y tiempos: el reto exige documentar
modelo, versión, parámetros, costo y limitaciones. Un fallo (red, HTTP, JSON roto) NUNCA
lanza: devuelve `Respuesta.error` y sin contenido, y el pipeline lo trata como abstención.
`ClienteFalso` sirve para tests sin Ollama. El LLM no recibe herramientas ni secretos.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

HOST_DEFECTO = "http://127.0.0.1:11434"
MODELO_DEFECTO = "qwen2.5:3b-instruct-q4_K_M"


@dataclass
class Respuesta:
    contenido: dict | None = None
    texto: str = ""
    modelo: str = ""
    opciones: dict = field(default_factory=dict)
    duracion_s: float = 0.0
    tokens_prompt: int = 0
    tokens_salida: int = 0
    tokens_por_segundo: float = 0.0
    error: str | None = None


class ClienteOllama:
    def __init__(
        self,
        modelo: str = MODELO_DEFECTO,
        host: str = HOST_DEFECTO,
        num_thread: int = 4,
        num_ctx: int = 4096,
        num_predict: int = 512,
        temperature: float = 0,
        seed: int = 7,
        timeout: float = 600,
    ):
        self.modelo = modelo
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.opciones = {
            "num_thread": num_thread, "num_ctx": num_ctx, "num_predict": num_predict,
            "temperature": temperature, "seed": seed,
        }

    def generar(self, sistema: str, usuario: str, esquema: dict) -> Respuesta:
        cuerpo = {
            "model": self.modelo, "stream": False, "format": esquema, "options": self.opciones,
            "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
        }
        base = Respuesta(modelo=self.modelo, opciones=dict(self.opciones))
        inicio = time.monotonic()
        try:
            peticion = urllib.request.Request(
                f"{self.host}/api/chat", json.dumps(cuerpo).encode(), {"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(peticion, timeout=self.timeout) as r:
                datos = json.load(r)
        except urllib.error.HTTPError as e:
            base.error = f"http_{e.code}"
            base.duracion_s = time.monotonic() - inicio
            return base
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            base.error = f"conexion: {e}"
            base.duracion_s = time.monotonic() - inicio
            return base
        except json.JSONDecodeError:
            base.error = "respuesta_http_invalida"
            base.duracion_s = time.monotonic() - inicio
            return base

        base.duracion_s = time.monotonic() - inicio
        base.texto = (datos.get("message") or {}).get("content", "")
        base.tokens_prompt = int(datos.get("prompt_eval_count") or 0)
        base.tokens_salida = int(datos.get("eval_count") or 0)
        eval_s = (datos.get("eval_duration") or 0) / 1e9
        base.tokens_por_segundo = (base.tokens_salida / eval_s) if eval_s else 0.0
        try:
            contenido = json.loads(base.texto)
        except json.JSONDecodeError:
            base.error = "json_invalido"
            return base
        if not isinstance(contenido, dict):
            base.error = "json_invalido"
            return base
        base.contenido = contenido
        return base


class ClienteFalso:
    """Devuelve respuestas predefinidas en orden (dict, JSON en texto o `Respuesta`)."""

    def __init__(self, respuestas: list):
        self._respuestas = list(respuestas)
        self.modelo = "falso"
        self.llamadas: list[tuple] = []

    def generar(self, sistema: str, usuario: str, esquema: dict) -> Respuesta:
        self.llamadas.append((sistema, usuario, esquema))
        if not self._respuestas:
            return Respuesta(modelo=self.modelo, error="sin_respuestas_configuradas")
        siguiente = self._respuestas.pop(0)
        if isinstance(siguiente, Respuesta):
            return siguiente
        contenido = json.loads(siguiente) if isinstance(siguiente, str) else siguiente
        return Respuesta(contenido=contenido, texto=json.dumps(contenido, ensure_ascii=False), modelo=self.modelo)


def cliente_desde_entorno() -> ClienteOllama:
    """Configura el cliente con LLM_MODELO, OLLAMA_HOST, LLM_NUM_THREAD, LLM_NUM_CTX, LLM_NUM_PREDICT."""
    env = os.environ
    return ClienteOllama(
        modelo=env.get("LLM_MODELO", MODELO_DEFECTO),
        host=env.get("OLLAMA_HOST", HOST_DEFECTO),
        num_thread=int(env.get("LLM_NUM_THREAD", 4)),
        num_ctx=int(env.get("LLM_NUM_CTX", 4096)),
        num_predict=int(env.get("LLM_NUM_PREDICT", 512)),
    )
