"""Read-only data access for the Streamlit inbox."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb


class ScoreUnavailableError(RuntimeError):
    """The TAR-008 scoring output is not available for the inbox."""


@dataclass(frozen=True)
class InboxGroup:
    """A scored news group ready for the priority inbox."""

    grupo_id: str
    titulo_representativo: str
    n_noticias: int
    n_procedencias: int
    fecha_max: object
    corroboracion: int
    es_repeticion: bool
    tema: str
    R: float
    I: float  # noqa: E741 - TAR-008 contract name
    U: float
    N: float
    E: float
    puntaje: float
    prioridad: str
    estado_evidencia: str
    version_reglas: str
    motivos: str


@contextmanager
def open_inbox_repository(
    motor_path: str | Path, signals_path: str | Path
) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Open the motor repository and its signals dependency without write access."""

    connection = duckdb.connect(str(motor_path), read_only=True)
    try:
        connection.sql(_read_only_attach_query(signals_path))
        yield connection
    finally:
        connection.close()


def _read_only_attach_query(signals_path: str | Path) -> str:
    """Build the escaped ATTACH statement required by DuckDB's grammar."""

    escaped_path = str(signals_path).replace("'", "''")
    return "ATTACH '__SIGNALS_PATH__' AS senales (READ_ONLY)".replace(
        "__SIGNALS_PATH__", escaped_path
    )


def fetch_inbox_groups(
    motor_path: str | Path,
    signals_path: str | Path,
    *,
    topic: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50,
) -> list[InboxGroup]:
    """Return TAR-008-scored, non-``otros`` groups in priority order."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    query = """
        SELECT
            g.grupo_id, g.titulo_representativo, g.n_noticias, g.n_procedencias,
            g.fecha_max, g.corroboracion, g.es_repeticion, p.tema,
            p.R, p.I, p.U, p.N, p.E, p.puntaje, p.prioridad,
            p.estado_evidencia, p.version_reglas, p.motivos
        FROM grupos AS g
        JOIN puntaje AS p ON p.grupo_id = g.grupo_id
        WHERE p.tema <> 'otros'
            AND (? IS NULL OR p.tema = ?)
            AND (? IS NULL OR CAST(g.fecha_max AS DATE) >= ?)
            AND (? IS NULL OR CAST(g.fecha_max AS DATE) <= ?)
        ORDER BY p.puntaje DESC, p.U DESC, g.grupo_id ASC
        LIMIT ?
    """
    parameters = [topic, topic, start_date, start_date, end_date, end_date, limit]
    try:
        with open_inbox_repository(motor_path, signals_path) as connection:
            rows = connection.sql(query, params=parameters).fetchall()
    except duckdb.CatalogException as error:
        raise ScoreUnavailableError(
            "No hay puntajes TAR-008 disponibles. Ejecute el motor de puntaje."
        ) from error

    return [InboxGroup(*row) for row in rows]


def fetch_inbox_filter_options(
    motor_path: str | Path, signals_path: str | Path
) -> tuple[list[str], date | None, date | None]:
    """Return uncapped topics and date bounds for query-level inbox filters."""

    query = """
        SELECT p.tema, CAST(g.fecha_max AS DATE)
        FROM grupos AS g
        JOIN puntaje AS p ON p.grupo_id = g.grupo_id
        WHERE p.tema <> 'otros' AND g.fecha_max IS NOT NULL
    """
    try:
        with open_inbox_repository(motor_path, signals_path) as connection:
            rows = connection.sql(query).fetchall()
    except duckdb.CatalogException as error:
        raise ScoreUnavailableError(
            "No hay puntajes TAR-008 disponibles. Ejecute el motor de puntaje."
        ) from error

    if not rows:
        with open_inbox_repository(motor_path, signals_path) as connection:
            availability = connection.sql(
                "SELECT EXISTS(SELECT 1 FROM grupos), EXISTS(SELECT 1 FROM puntaje)"
            ).fetchone()
        if availability is None:
            raise ScoreUnavailableError("No se pudo comprobar el motor de puntaje.")
        has_groups, has_scores = availability
        if has_groups and not has_scores:
            raise ScoreUnavailableError(
                "No hay puntajes TAR-008 disponibles. Ejecute el motor de puntaje."
            )
    dates = [row[1] for row in rows]
    return sorted({row[0] for row in rows}), min(dates, default=None), max(dates, default=None)
