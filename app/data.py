"""Read-only data access for the Streamlit inbox."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb


@dataclass(frozen=True)
class InboxGroup:
    """A news group ready for the priority inbox."""

    grupo_id: str
    titulo_representativo: str
    n_noticias: int
    n_procedencias: int
    fecha_max: object
    corroboracion: int
    es_repeticion: bool
    tema: str


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
    """Return groups whose dominant embeddings topic is eligible for the inbox."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    parameters = [
        topic,
        topic,
        start_date,
        start_date,
        end_date,
        end_date,
        limit,
    ]

    query = """
        WITH topic_counts AS (
            SELECT
                gn.grupo_id,
                c.tema,
                COUNT(*) AS n_clasificaciones
            FROM grupo_noticias AS gn
            JOIN clasificacion AS c
                ON c.id_noticia = gn.id_noticia
                AND c.metodo = 'embeddings'
            GROUP BY gn.grupo_id, c.tema
        ), ranked_topics AS (
            SELECT
                grupo_id,
                tema,
                ROW_NUMBER() OVER (
                    PARTITION BY grupo_id
                    ORDER BY n_clasificaciones DESC, tema ASC
                ) AS topic_rank
            FROM topic_counts
        )
        SELECT
            g.grupo_id,
            g.titulo_representativo,
            g.n_noticias,
            g.n_procedencias,
            g.fecha_max,
            g.corroboracion,
            g.es_repeticion,
            ranked_topics.tema
        FROM grupos AS g
        JOIN ranked_topics ON ranked_topics.grupo_id = g.grupo_id
        WHERE ranked_topics.topic_rank = 1
            AND ranked_topics.tema <> 'otros'
            AND (? IS NULL OR ranked_topics.tema = ?)
            AND (? IS NULL OR CAST(g.fecha_max AS DATE) >= ?)
            AND (? IS NULL OR CAST(g.fecha_max AS DATE) <= ?)
        ORDER BY
            g.fecha_max DESC NULLS LAST,
            g.n_procedencias DESC NULLS LAST,
            g.grupo_id ASC
        LIMIT ?
    """

    with open_inbox_repository(motor_path, signals_path) as connection:
        rows = connection.execute(query, parameters).fetchall()

    return [InboxGroup(*row) for row in rows]
