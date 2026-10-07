"""Pruebas de la derivación de épicas y validación de notion_sync.py; no usan internet."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import notion_sync as ns  # noqa: E402


def _epica(id_, estado=None):
    return {"id": id_, "tarea": id_, "responsable": "Guille", "estado": estado or "Pendiente",
            "fecha": "2026-10-06", "notas": "", "tipo": "Épica", "epica": ""}


def _tarea(id_, epica, estado):
    return {"id": id_, "tarea": id_, "responsable": "Guille", "estado": estado,
            "fecha": "2026-10-06", "notas": "", "tipo": "Tarea", "epica": epica}


def test_progreso_epica_parcial():
    items = [
        _epica("EPI-001"),
        _tarea("TAR-001", "EPI-001", "Hecho"),
        _tarea("TAR-002", "EPI-001", "Hecho"),
        _tarea("TAR-003", "EPI-001", "Hecho"),
        _tarea("TAR-004", "EPI-001", "Pendiente"),
        _tarea("TAR-005", "EPI-001", "Pendiente"),
    ]
    out = ns.progreso_epicas(items)
    epi = next(i for i in out if i["id"] == "EPI-001")
    assert epi["progreso"] == "██████░░░░ 60% (3/5)"
    assert epi["estado"] == "En curso"


def test_estado_epica_todas_hechas():
    items = [_epica("EPI-001"), _tarea("TAR-001", "EPI-001", "Hecho"),
             _tarea("TAR-002", "EPI-001", "Hecho")]
    epi = ns.progreso_epicas(items)[0]
    assert epi["estado"] == "Hecho"
    assert epi["progreso"] == "██████████ 100% (2/2)"


def test_estado_epica_bloqueada_sin_en_curso():
    items = [_epica("EPI-001"), _tarea("TAR-001", "EPI-001", "Pendiente"),
             _tarea("TAR-002", "EPI-001", "Bloqueada")]
    epi = ns.progreso_epicas(items)[0]
    assert epi["estado"] == "Bloqueada"


def test_estado_epica_en_curso_prevalece_sobre_bloqueada():
    items = [_epica("EPI-001"), _tarea("TAR-001", "EPI-001", "En curso"),
             _tarea("TAR-002", "EPI-001", "Bloqueada")]
    epi = ns.progreso_epicas(items)[0]
    assert epi["estado"] == "En curso"


def test_estado_epica_sin_hijos():
    items = [_epica("EPI-001")]
    epi = ns.progreso_epicas(items)[0]
    assert epi["estado"] == "Pendiente"
    assert epi["progreso"] == "░░░░░░░░░░ 0% (0/0)"


def test_progreso_epicas_no_toca_tareas():
    items = [_epica("EPI-001"), _tarea("TAR-001", "EPI-001", "Hecho")]
    out = ns.progreso_epicas(items)
    tarea = next(i for i in out if i["id"] == "TAR-001")
    assert "progreso" not in tarea


def test_validar_detecta_epica_colgante():
    datos = {"tareas": [
        {"ID": "TAR-001", "Tarea": "x", "Tipo": "Tarea", "Épica": "EPI-999"},
    ]}
    assert ns.validar(datos) == 1


def test_validar_sin_errores_cuando_epica_existe():
    datos = {"tareas": [
        {"ID": "EPI-001", "Tarea": "epi", "Tipo": "Épica", "Épica": ""},
        {"ID": "TAR-001", "Tarea": "x", "Tipo": "Tarea", "Épica": "EPI-001"},
    ]}
    assert ns.validar(datos) == 0


def test_cargar_todo_carga_tareas_yaml_real():
    datos = ns.cargar_todo()
    assert len(datos["tareas"]) >= 17  # 5 épicas + 12 tareas existentes
    epicas = [t for t in datos["tareas"] if t.get("Tipo") == "Épica"]
    tareas = [t for t in datos["tareas"] if t.get("Tipo") == "Tarea"]
    assert len(epicas) >= 5
    assert len(tareas) >= 12
    estados_validos = {"Pendiente", "En curso", "Hecho", "Bloqueada"}
    for epi in epicas:
        assert epi.get("Progreso")
        assert epi.get("Estado") in estados_validos
    assert ns.validar(datos) == 0
