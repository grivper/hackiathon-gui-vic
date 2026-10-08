"""Abstención decidida por código, antes de llamar al LLM (TAR-009, G3).

Si no hay evidencia sustentada el sistema se abstiene: no se llama al modelo y no se
rellena nada (CU-04, T06). Al consultar un indicador del Banco Mundial hay tres
abstenciones: el indicador no está en el corpus (`indicador_ausente`), existe pero el
valor es nulo (`valor_nulo`, nunca se reemplaza por cero) o el año está fuera del rango
disponible (`anio_fuera_de_rango`). Todo borrador declara su alcance (T09): si solo hay
titulares, dice "basado únicamente en titular/metadatos".
"""
from __future__ import annotations

from pathlib import Path

import duckdb

ALCANCE_TITULARES = "basado únicamente en titular/metadatos"
ALCANCE_CON_OFICIALES = "basado en titular/metadatos y datos oficiales citados (indicadores anuales o eventos USGS)"
NOTA_DATO_ANUAL = "dato anual del año indicado: no es una medición actual"


def alcance_de(paquete: dict) -> str:
    """Alcance honesto del borrador según el tipo de evidencia disponible."""
    tipos = {i["tipo"] for i in paquete["items"]}
    return ALCANCE_CON_OFICIALES if tipos & {"indicador", "evento"} else ALCANCE_TITULARES


def _abstencion(motivo: str, vacio: str, alcance: str) -> dict:
    return {
        "tipo_respuesta": "abstencion", "motivo": motivo, "afirmaciones": [],
        "versiones": [], "vacios": [vacio], "alcance": alcance,
    }


def decidir_abstencion_grupo(paquete: dict) -> dict | None:
    """Abstención para un grupo sin evidencia citable; None si se puede intentar un borrador."""
    if paquete["items"]:
        return None
    return _abstencion(
        "sin_evidencia", "No hay evidencia citable para este grupo.", ALCANCE_TITULARES
    )


def consultar_indicador(
    indicador_id: str, anio: int, senales_db: Path, pais_iso3: str = "PAN"
) -> dict:
    """Consulta exacta (sin LLM) de un indicador y año: devuelve el ítem citable o la
    abstención correspondiente. Solo lectura."""
    con = duckdb.connect(str(senales_db), read_only=True)
    try:
        filas = con.execute(
            """SELECT id_evidencia, indicador_nombre, anio, valor, unidad, fuente_url
               FROM indicadores WHERE pais_iso3 = ? AND indicador_id = ? ORDER BY anio""",
            [pais_iso3, indicador_id],
        ).fetchall()
    finally:
        con.close()

    if not filas:
        return _abstencion(
            "indicador_ausente", f"El indicador {indicador_id} no está en el corpus.", ALCANCE_TITULARES
        )
    anios = [f[2] for f in filas]
    if not (min(anios) <= anio <= max(anios)):
        return _abstencion(
            "anio_fuera_de_rango",
            f"No hay datos de {indicador_id} para {anio}; el rango disponible es {min(anios)}-{max(anios)}.",
            ALCANCE_CON_OFICIALES,
        )
    fila = next((f for f in filas if f[2] == anio), None)
    if fila is None or fila[3] is None:
        return _abstencion(
            "valor_nulo", f"El valor de {indicador_id} para {anio} no está disponible (nulo).",
            ALCANCE_CON_OFICIALES,
        )
    return {
        "tipo_respuesta": "respuesta",
        "items": [{
            "id_evidencia": fila[0], "tipo": "indicador",
            "campos": {"indicador_nombre": fila[1], "anio": fila[2], "valor": fila[3],
                       "unidad": fila[4], "fuente_url": fila[5]},
        }],
        "nota": NOTA_DATO_ANUAL,
        "alcance": ALCANCE_CON_OFICIALES,
    }
