"""Pruebas de motor/cargar_db.py: validación (T01), idempotencia y fallos fatales."""
import json
import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import motor.cargar_db as cargar_db  # noqa: E402

FIXTURE_NOTICIAS = Path(__file__).parent / "fixtures" / "db_noticias_invalidas.csv"

INDICADORES_CSV = (
    "id_evidencia,pais_iso3,indicador_id,indicador_nombre,anio,valor,unidad,observacion,"
    "fuente_url,fecha_extraccion,licencia\n"
    "IND-PAN-X-2020,PAN,X,Indicador X,2020,1.5,% anual,,https://ejemplo.com/x,"
    "2026-01-05T10:06:00Z,CC BY 4.0\n"
)

EXCLUIDOS_CSV = "origen,_archivo,titulo,url,fecha_publicacion,fecha_deteccion,motivo\n"

EVENTOS_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "us0001",
            "geometry": {"type": "Point", "coordinates": [-82.0, 8.0, 10.0]},
            "properties": {
                "id": "us0001", "magnitude": 4.1, "time": "2026-01-05T10:00:00Z",
                "updated": "2026-01-05T11:00:00Z", "longitude": -82.0, "latitude": 8.0,
                "depth": 10.0, "place": "Panama", "status": "reviewed",
                "url": "https://example.com/us0001",
            },
        }
    ],
}


def preparar_data_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    processed = data_dir / "processed"
    processed.mkdir(parents=True)
    (processed / "noticias.csv").write_text(FIXTURE_NOTICIAS.read_text(encoding="utf-8"), encoding="utf-8")
    (processed / "indicadores.csv").write_text(INDICADORES_CSV, encoding="utf-8")
    (processed / "excluidos.csv").write_text(EXCLUIDOS_CSV, encoding="utf-8")
    (processed / "eventos.geojson").write_text(json.dumps(EVENTOS_GEOJSON), encoding="utf-8")
    (data_dir / "manifest.json").write_text(json.dumps({"version": "test", "fecha_corte_utc": "2026-01-05T10:06:00Z"}), encoding="utf-8")
    return data_dir


def test_validacion_t01_rechaza_filas_malas_y_conserva_nulos(tmp_path):
    data_dir = preparar_data_dir(tmp_path)
    db_path = tmp_path / "senales.duckdb"

    codigo = cargar_db.main(["--data-dir", str(data_dir), "--db", str(db_path)])
    assert codigo == 0

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        noticias = con.execute("SELECT id_noticia, titulo, fecha_publicacion FROM noticias ORDER BY id_noticia").fetchall()
        # N-002 (fecha inválida), N-004 (sin url) y el N-001 duplicado quedan fuera.
        assert [n[0] for n in noticias] == ["N-001", "N-003"]

        n3 = next(n for n in noticias if n[0] == "N-003")
        assert n3[1] is None  # titulo vacío -> NULL conservado
        assert n3[2] is None  # fecha_publicacion vacía -> NULL conservado, no es error

        rechazados = con.execute("SELECT id, campo, motivo FROM rechazados ORDER BY id, campo").fetchall()
        motivos = {(r[0], r[1]) for r in rechazados}
        assert ("N-002", "fecha_publicacion") in motivos
        assert ("N-004", "url") in motivos
        assert ("N-001", "id_noticia") in motivos  # fila duplicada rechazada

        assert con.execute("SELECT count(*) FROM eventos").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM indicadores").fetchone()[0] == 1
    finally:
        con.close()

    assert (db_path.parent / "reporte_calidad.md").exists()


def test_idempotencia_sin_cambios_y_forzar_reconstruye(tmp_path, capsys):
    data_dir = preparar_data_dir(tmp_path)
    db_path = tmp_path / "senales.duckdb"

    assert cargar_db.main(["--data-dir", str(data_dir), "--db", str(db_path)]) == 0
    capsys.readouterr()
    mtime_1 = db_path.stat().st_mtime_ns

    codigo = cargar_db.main(["--data-dir", str(data_dir), "--db", str(db_path)])
    salida = capsys.readouterr().out
    assert codigo == 0
    assert "sin cambios" in salida
    assert db_path.stat().st_mtime_ns == mtime_1

    codigo = cargar_db.main(["--data-dir", str(data_dir), "--db", str(db_path), "--forzar"])
    salida = capsys.readouterr().out
    assert codigo == 0
    assert "sin cambios" not in salida


def test_archivo_de_entrada_faltante_es_fatal(tmp_path):
    data_dir = preparar_data_dir(tmp_path)
    (data_dir / "processed" / "indicadores.csv").unlink()
    db_path = tmp_path / "senales.duckdb"

    codigo = cargar_db.main(["--data-dir", str(data_dir), "--db", str(db_path)])
    assert codigo != 0
    assert not db_path.exists()


NOTICIAS_RANGO_CSV = (
    "id_noticia,titulo,url,medio,idioma,fecha_publicacion,fecha_deteccion,fecha_extraccion,tema,origen,alcance_texto\n"
    "R-ANTES,Antes,https://e.com/1,e.com,es,2023-12-31T23:59:59Z,,2026-01-05T10:00:00Z,,tvn_rss,t\n"
    "R-INICIO,Inicio,https://e.com/2,e.com,es,2024-01-01T00:00:00Z,,2026-01-05T10:00:00Z,,tvn_rss,t\n"
    "R-DENTRO,Dentro,https://e.com/3,e.com,es,2025-02-10T08:00:00-05:00,,2026-01-05T10:00:00Z,,tvn_rss,t\n"
    "R-FIN,Fin,https://e.com/4,e.com,es,2025-10-01T00:00:00Z,,2026-01-05T10:00:00Z,,tvn_rss,t\n"
    "R-NULA,Sin fecha,https://e.com/5,e.com,es,,,2026-01-05T10:00:00Z,,tvn_rss,t\n"
)


def test_rango_envia_fuera_de_rango_a_excluidos(tmp_path):
    data_dir = preparar_data_dir(tmp_path)
    (data_dir / "processed" / "noticias.csv").write_text(NOTICIAS_RANGO_CSV, encoding="utf-8")
    db_path = tmp_path / "senales.duckdb"

    codigo = cargar_db.main([
        "--data-dir", str(data_dir), "--db", str(db_path), "--rango", "2024-01-01", "2025-10-01",
    ])
    assert codigo == 0

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        ids = [r[0] for r in con.execute("SELECT id_noticia FROM noticias ORDER BY id_noticia").fetchall()]
        # [desde, hasta): el inicio entra, el fin sale; la fecha nula se conserva (no se inventa).
        assert ids == ["R-DENTRO", "R-INICIO", "R-NULA"]
        excl = con.execute("SELECT titulo, url, motivo FROM excluidos ORDER BY titulo").fetchall()
        assert [e[0] for e in excl] == ["Antes", "Fin"]
        assert all("fuera de rango" in e[2] for e in excl)
    finally:
        con.close()


def test_sin_rango_no_filtra_y_rango_invalido_es_fatal(tmp_path):
    data_dir = preparar_data_dir(tmp_path)
    (data_dir / "processed" / "noticias.csv").write_text(NOTICIAS_RANGO_CSV, encoding="utf-8")
    db_path = tmp_path / "senales.duckdb"
    assert cargar_db.main(["--data-dir", str(data_dir), "--db", str(db_path)]) == 0
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        assert con.execute("SELECT count(*) FROM noticias").fetchone()[0] == 5
    finally:
        con.close()

    with pytest.raises(SystemExit):
        cargar_db.main(["--data-dir", str(data_dir), "--db", str(db_path), "--rango", "2025-10-01", "2024-01-01"])


def test_rango_reconstruye_aunque_el_manifest_no_cambie(tmp_path):
    data_dir = preparar_data_dir(tmp_path)
    (data_dir / "processed" / "noticias.csv").write_text(NOTICIAS_RANGO_CSV, encoding="utf-8")
    db_path = tmp_path / "senales.duckdb"
    assert cargar_db.main(["--data-dir", str(data_dir), "--db", str(db_path)]) == 0
    assert cargar_db.main(["--data-dir", str(data_dir), "--db", str(db_path), "--rango", "2024-01-01", "2025-10-01"]) == 0
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        assert con.execute("SELECT count(*) FROM noticias").fetchone()[0] == 3
    finally:
        con.close()
