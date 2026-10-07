"""Validador determinista de citas (TAR-009, G2).

El LLM solo redacta; este módulo decide qué afirmaciones sobreviven. Una afirmación se
conserva solo si:
  - tiene `texto` no vacío y `tipo` en {hecho, declaracion, inferencia, hipotesis},
  - cita un `id_evidencia` presente en el paquete de evidencia de ESTE grupo,
  - nombra un `campo` que existe y no es nulo en ese ítem,
  - cada cifra de su texto aparece en los valores del ítem citado (redondeo permitido).
Todo lo demás se descarta con un motivo registrado. Si ninguna afirmación sobrevive, la
respuesta efectiva pasa a `abstencion`: nunca se rellena ni se corrige lo que dijo el LLM.
"""
from __future__ import annotations

import re

TIPOS_RESPUESTA = {"respuesta", "abstencion", "contradiccion"}
TIPOS_AFIRMACION = {"hecho", "declaracion", "inferencia", "hipotesis"}
_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


def _candidatos(token: str) -> list[tuple[float, int]]:
    """Interpretaciones numéricas de un token: (valor, decimales). '1.400' puede ser 1,4 o 1400."""
    candidatos = []
    decimal = token.replace(",", ".")
    decimales = len(decimal.split(".")[1]) if "." in decimal else 0
    candidatos.append((float(decimal), decimales))
    miles = token.replace(".", "").replace(",", "")
    if miles != token:
        candidatos.append((float(miles), 0))
    return candidatos


def _numeros_del_item(item: dict) -> list[float]:
    numeros: list[float] = []
    for valor in item["campos"].values():
        if isinstance(valor, bool) or valor is None:
            continue
        if isinstance(valor, (int, float)):
            numeros.append(float(valor))
        else:
            numeros += [float(t.replace(",", ".")) for t in _NUMERO.findall(str(valor))]
    return numeros


def _cifras_sustentadas(texto: str, item: dict) -> bool:
    disponibles = _numeros_del_item(item)
    for token in _NUMERO.findall(texto):
        if not any(
            round(v, dec) == num for num, dec in _candidatos(token) for v in disponibles
        ):
            return False
    return True


def _motivo_de_descarte(afirmacion: object, items: dict[str, dict]) -> str | None:
    if not isinstance(afirmacion, dict):
        return "afirmacion_invalida"
    texto = afirmacion.get("texto")
    if not isinstance(texto, str) or not texto.strip():
        return "texto_vacio"
    if afirmacion.get("tipo") not in TIPOS_AFIRMACION:
        return "tipo_invalido"
    id_evidencia = afirmacion.get("id_evidencia")
    campo = afirmacion.get("campo")
    if not id_evidencia or not campo:
        return "sin_cita"
    item = items.get(id_evidencia)
    if item is None:
        return "evidencia_inexistente"
    if campo not in item["campos"]:
        return "campo_inexistente"
    if item["campos"][campo] is None:
        return "campo_nulo"
    if not _cifras_sustentadas(texto, item):
        return "cifra_no_sustentada"
    return None


def _resultado_invalido(errores: list[str]) -> dict:
    return {
        "valida": False, "tipo_respuesta": "abstencion", "afirmaciones": [], "descartadas": [],
        "cobertura": 0.0, "versiones": [], "vacios": [], "errores_esquema": errores,
    }


def validar_citas(salida: object, paquete: dict) -> dict:
    """Valida la salida estructurada del LLM contra el paquete de evidencia (ver módulo)."""
    if not isinstance(salida, dict):
        return _resultado_invalido(["la salida no es un objeto JSON"])
    errores = []
    if salida.get("tipo_respuesta") not in TIPOS_RESPUESTA:
        errores.append("tipo_respuesta ausente o fuera de {respuesta, abstencion, contradiccion}")
    if not isinstance(salida.get("afirmaciones"), list):
        errores.append("afirmaciones debe ser una lista")
    if errores:
        return _resultado_invalido(errores)

    items = {i["id_evidencia"]: i for i in paquete["items"]}
    conservadas, descartadas = [], []
    for afirmacion in salida["afirmaciones"]:
        motivo = _motivo_de_descarte(afirmacion, items)
        if motivo:
            descartadas.append({"afirmacion": afirmacion, "motivo": motivo})
        else:
            conservadas.append(afirmacion)

    total = len(salida["afirmaciones"])
    tipo = salida["tipo_respuesta"]
    if tipo == "respuesta" and not conservadas:
        tipo = "abstencion"
    return {
        "valida": True,
        "tipo_respuesta": tipo,
        "afirmaciones": conservadas,
        "descartadas": descartadas,
        "cobertura": (len(conservadas) / total) if total else 0.0,
        "versiones": salida.get("versiones") if isinstance(salida.get("versiones"), list) else [],
        "vacios": salida.get("vacios") if isinstance(salida.get("vacios"), list) else [],
        "errores_esquema": [],
    }
