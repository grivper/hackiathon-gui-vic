"""On-demand draft generation for one group, used by the "Generar borrador" button.

Reuses the motor's pipeline (`motor.generar`) unchanged. Three guards matter here:
a ficha already reviewed by a person is never overwritten, a transient model failure
is never persisted as if it were an editorial abstention, and saving touches only the
requested group (`guardar_ficha`), so the committed `fichas.jsonl` keeps every other line.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from motor import generar, llm  # noqa: E402

DEFAULT_RULES_PATH = ROOT_DIR / "motor" / "reglas_puntaje.yaml"


@dataclass(frozen=True)
class GenerationResult:
    """``status``: generada | ya_revisada | error_modelo."""

    status: str
    ficha: dict | None = None
    detail: str = ""


def estado_ollama(
    host: str | None = None, modelo: str | None = None, timeout: float = 1.5
) -> tuple[bool, str]:
    """Whether the local LLM can be used right now; the second item explains why not."""

    import os

    host = (host or os.environ.get("OLLAMA_HOST", llm.HOST_DEFECTO)).rstrip("/")
    modelo = modelo or os.environ.get("LLM_MODELO", llm.MODELO_DEFECTO)
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=timeout) as response:
            names = {m.get("name") for m in json.load(response).get("models", [])}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False, f"Ollama no responde en {host}. Inícielo para generar borradores."
    if modelo not in names:
        return False, f"Ollama está activo, pero falta el modelo {modelo}."
    return True, ""


def generar_borrador(
    grupo_id: str,
    motor_path: str | Path,
    signals_path: str | Path,
    fichas_path: str | Path,
    *,
    reglas_path: str | Path = DEFAULT_RULES_PATH,
    cliente=None,
) -> GenerationResult:
    """Generate and save the ficha of a single group."""

    motor_path, signals_path, fichas_path = Path(motor_path), Path(signals_path), Path(fichas_path)
    existing = generar.estados_existentes(motor_path).get(grupo_id)
    if existing in generar.ESTADOS_REVISADOS:
        return GenerationResult("ya_revisada", detail=f"Estado actual: {existing}.")

    rules = yaml.safe_load(Path(reglas_path).read_text(encoding="utf-8"))
    client = cliente or llm.cliente_desde_entorno()
    ficha = generar.generar_ficha(grupo_id, client, motor_path, signals_path, rules)
    if ficha.get("motivo_abstencion") == "llm_error":
        vacios = ficha.get("vacios") or []
        return GenerationResult("error_modelo", detail=" ".join(vacios))
    generar.guardar_ficha(motor_path, ficha, fichas_path)
    return GenerationResult("generada", ficha)
