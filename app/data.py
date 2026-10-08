"""Read-only data access for the Streamlit inbox."""

from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import duckdb


#: The 5 review states mandated by the brief. Order matters for the selectbox.
VALID_REVIEW_STATES = (
    "nuevo",
    "en revisión",
    "requiere evidencia",
    "aprobado como borrador",
    "descartado",
)


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
    contexto_oficial: str | None
    evento_usgs_id: str | None


DEFAULT_FICHAS_PATH = Path("data/fichas.jsonl")
_ABSTENTION_MESSAGE = "No hay evidencia validada en esta ficha para responder a esa consulta."
_QUERY_STOP_WORDS = frozenset({
    "como", "con", "cual", "cuales", "cuando", "donde", "este", "esta", "ficha",
    "grupo", "hay", "las", "los", "para", "paso", "que", "quien", "sobre", "una",
    "uno", "unos", "unas",
})


@dataclass(frozen=True)
class GroupFicha:
    """A normalized generated ficha and the provenance that governs writes."""

    id_caso: str
    estado_revision: str
    tipo_respuesta: str  # respuesta | abstencion | contradiccion
    borrador: str | None
    citas: list[tuple[str, str]]  # (id_evidencia, campo)
    afirmaciones: list[str]
    motivo_abstencion: str | None
    generado_en: datetime | None
    source: str = "duckdb"
    persistable: bool = True
    claim_citations: list[tuple[str, list[str]]] = field(default_factory=list)


def _normalize_ficha(
    payload: object,
    *,
    source: str,
    estado_revision: object | None = None,
    tipo_respuesta: object | None = None,
    generado_en: datetime | None = None,
) -> GroupFicha | None:
    """Accept only a ficha-shaped record; never manufacture missing content."""

    if not isinstance(payload, dict) or not isinstance(payload.get("id_caso"), str):
        return None
    raw_citas = payload.get("citas", [])
    raw_claims = payload.get("afirmaciones", [])
    if not isinstance(raw_citas, list) or not isinstance(raw_claims, list):
        return None
    citas = [
        (cita["id_evidencia"], cita["campo"])
        for cita in raw_citas
        if isinstance(cita, dict)
        and isinstance(cita.get("id_evidencia"), str)
        and isinstance(cita.get("campo"), str)
    ]
    valid_citation_ids = {citation_id for citation_id, _ in citas}
    afirmaciones: list[str] = []
    claim_citations: list[tuple[str, list[str]]] = []
    for claim in raw_claims:
        if not isinstance(claim, dict) or not isinstance(claim.get("texto"), str):
            continue
        text = claim["texto"]
        citation_id = claim.get("id_evidencia")
        citations_for_claim = (
            [citation_id]
            if isinstance(citation_id, str) and citation_id in valid_citation_ids
            else []
        )
        afirmaciones.append(text)
        claim_citations.append((text, citations_for_claim))

    resolved_state = estado_revision if estado_revision is not None else payload.get("estado_revision")
    resolved_type = tipo_respuesta if tipo_respuesta is not None else payload.get("tipo_respuesta")
    if not isinstance(resolved_state, str) or not isinstance(resolved_type, str):
        return None
    borrador = payload.get("borrador")
    motivo = payload.get("motivo_abstencion")
    if borrador is not None and not isinstance(borrador, str):
        return None
    if motivo is not None and not isinstance(motivo, str):
        return None
    return GroupFicha(
        id_caso=payload["id_caso"], estado_revision=resolved_state,
        tipo_respuesta=resolved_type, borrador=borrador, citas=citas,
        afirmaciones=afirmaciones, motivo_abstencion=motivo,
        generado_en=generado_en, source=source, persistable=source == "duckdb",
        claim_citations=claim_citations,
    )


def _read_jsonl_ficha(fichas_path: str | Path, grupo_id: str) -> GroupFicha | None:
    """Read one matching committed ficha, treating any malformed JSONL as absent."""

    try:
        lines = Path(fichas_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    matched: dict[str, object] | None = None
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(record, dict):
            return None
        if record.get("id_caso") == grupo_id:
            matched = record
    return _normalize_ficha(matched, source="jsonl") if matched else None


def fetch_group_ficha(
    motor_path: str | Path,
    signals_path: str | Path,
    grupo_id: str,
    *,
    fichas_path: str | Path = DEFAULT_FICHAS_PATH,
) -> GroupFicha | None:
    """Return a DuckDB ficha first, then the committed read-only JSONL fallback."""

    del signals_path
    row = None
    try:
        with duckdb.connect(str(motor_path), read_only=True) as connection:
            row = connection.sql(
                "SELECT id_caso, estado_revision, tipo_respuesta, ficha, generado_en "
                "FROM fichas WHERE id_caso = ?", params=[grupo_id]
            ).fetchone()
    except duckdb.CatalogException:
        pass
    if row is not None:
        id_caso, estado_revision, tipo_respuesta, ficha_json, generado_en = row
        try:
            payload = json.loads(ficha_json) if ficha_json else {}
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            payload["id_caso"] = id_caso
        return _normalize_ficha(
            payload, source="duckdb", estado_revision=estado_revision,
            tipo_respuesta=tipo_respuesta, generado_en=generado_en,
        )
    return _read_jsonl_ficha(fichas_path, grupo_id)


def persist_ficha_review_state(
    motor_path: str | Path,
    grupo_id: str,
    new_state: str,
    *,
    ficha: GroupFicha | None = None,
) -> bool:
    """Persist only a DuckDB-backed ficha review state; JSONL fallback is read-only."""

    if new_state not in VALID_REVIEW_STATES:
        raise ValueError(f"Estado de revisión inválido: {new_state!r}")
    if ficha is not None and not ficha.persistable:
        return False
    try:
        with duckdb.connect(str(motor_path), read_only=False) as connection:
            updated = connection.execute(
                "UPDATE fichas SET estado_revision = ? WHERE id_caso = ? RETURNING id_caso",
                [new_state, grupo_id],
            ).fetchone()
    except duckdb.CatalogException:
        return False
    return updated is not None


@dataclass(frozen=True)
class ChatResponse:
    """A deterministic extractive response with validated citation IDs."""

    respuesta: str
    abstencion: bool
    citas: list[str]


def _query_terms(text: str) -> set[str]:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return {
        term for term in re.findall(r"[a-z0-9]+", normalized)
        if len(term) > 2 and term not in _QUERY_STOP_WORDS
    }


def ask_group_question(
    grupo_id: str,
    question: str,
    *,
    motor_path: str | Path | None = None,
    signals_path: str | Path | None = None,
    fichas_path: str | Path = DEFAULT_FICHAS_PATH,
) -> ChatResponse:
    """Extract a cited claim from this group's ficha or explicitly abstain."""

    if motor_path is None:
        return ChatResponse(_ABSTENTION_MESSAGE, True, [])
    ficha = fetch_group_ficha(
        motor_path, signals_path or "", grupo_id, fichas_path=fichas_path
    )
    question_terms = _query_terms(question)
    if ficha is not None and question_terms:
        for claim, citation_ids in ficha.claim_citations:
            if citation_ids and question_terms.intersection(_query_terms(claim)):
                return ChatResponse(claim, False, citation_ids)
    return ChatResponse(_ABSTENTION_MESSAGE, True, [])


@dataclass(frozen=True)
class EvidenceRow:
    """A read-only group member and its source metadata."""

    id_noticia: str
    titulo: str | None
    url: str | None
    medio: str | None
    procedencia: str | None
    fecha_publicacion: datetime | None
    fecha_deteccion: datetime | None
    similitud_al_centroide: float | None


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
            p.estado_evidencia, p.version_reglas, p.motivos,
            p.contexto_oficial, p.evento_usgs_id
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


def fetch_group_evidence(
    motor_path: str | Path, signals_path: str | Path, grupo_id: str
) -> list[EvidenceRow]:
    """Return group members in chronological editorial order.

    Publication dates remain null when the source does not provide one; detection
    dates are a separate metadata field and only order otherwise-undated rows.
    """

    query = """
        SELECT
            n.id_noticia, n.titulo, n.url, n.medio, gn.procedencia,
            n.fecha_publicacion, n.fecha_deteccion, gn.similitud_al_centroide
        FROM grupo_noticias AS gn
        JOIN senales.noticias AS n ON n.id_noticia = gn.id_noticia
        WHERE gn.grupo_id = ?
        ORDER BY
            n.fecha_publicacion ASC NULLS LAST,
            n.fecha_deteccion ASC NULLS LAST,
            n.id_noticia ASC
    """
    with open_inbox_repository(motor_path, signals_path) as connection:
        rows = connection.sql(query, params=[grupo_id]).fetchall()

    return [EvidenceRow(*row) for row in rows]


def fetch_inbox_filter_options(
    motor_path: str | Path, signals_path: str | Path
) -> tuple[list[str], date | None, date | None]:
    """Return uncapped topics and date bounds for query-level inbox filters.

    Topics and date bounds are computed in SQL (DISTINCT / MIN / MAX) instead
    of fetching every row, since only the aggregates are needed.
    """

    topics_query = """
        SELECT DISTINCT p.tema
        FROM grupos AS g
        JOIN puntaje AS p ON p.grupo_id = g.grupo_id
        WHERE p.tema <> 'otros' AND g.fecha_max IS NOT NULL
        ORDER BY p.tema
    """
    bounds_query = """
        SELECT MIN(CAST(g.fecha_max AS DATE)), MAX(CAST(g.fecha_max AS DATE))
        FROM grupos AS g
        JOIN puntaje AS p ON p.grupo_id = g.grupo_id
        WHERE p.tema <> 'otros' AND g.fecha_max IS NOT NULL
    """
    try:
        with open_inbox_repository(motor_path, signals_path) as connection:
            topics = [row[0] for row in connection.sql(topics_query).fetchall()]
            bounds = connection.sql(bounds_query).fetchone()
    except duckdb.CatalogException as error:
        raise ScoreUnavailableError(
            "No hay puntajes TAR-008 disponibles. Ejecute el motor de puntaje."
        ) from error

    if not topics:
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

    min_date, max_date = bounds if bounds else (None, None)
    return topics, min_date, max_date
