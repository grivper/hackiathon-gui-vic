"""Streamlit entry point for the editorial priority inbox."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import duckdb
import streamlit as st

from app.data import (
    InboxGroup,
    ScoreUnavailableError,
    fetch_inbox_filter_options,
    fetch_inbox_groups,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
MOTOR_PATH = ROOT_DIR / "data" / "motor.duckdb"
SIGNALS_PATH = ROOT_DIR / "data" / "senales.duckdb"


def database_fingerprint(
    motor_path: str | Path, signals_path: str | Path
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return a read-only cache identity for both DuckDB database files."""

    motor_stat = Path(motor_path).stat()
    signals_stat = Path(signals_path).stat()
    return (
        (motor_stat.st_mtime_ns, motor_stat.st_size),
        (signals_stat.st_mtime_ns, signals_stat.st_size),
    )


@st.cache_data
def load_inbox_filter_options(
    motor_path: str,
    signals_path: str,
    database_identity: tuple[tuple[int, int], tuple[int, int]],
) -> tuple[list[str], date | None, date | None]:
    """Cache uncapped filter choices until either database file changes."""

    return fetch_inbox_filter_options(motor_path, signals_path)


@st.cache_data
def load_inbox(
    motor_path: str,
    signals_path: str,
    database_identity: tuple[tuple[int, int], tuple[int, int]],
    topic: str | None,
    start_date: date | None,
    end_date: date | None,
) -> list[InboxGroup]:
    """Cache a read-only, query-level filtered inbox until the DB changes."""

    return fetch_inbox_groups(
        motor_path, signals_path, topic=topic, start_date=start_date, end_date=end_date
    )


def _group_date(group: InboxGroup) -> date | None:
    """Normalize DuckDB date values for Streamlit's date controls."""

    if isinstance(group.fecha_max, datetime):
        return group.fecha_max.date()
    if isinstance(group.fecha_max, date):
        return group.fecha_max
    return None


def editorial_guidance(prioridad: str, estado_evidencia: str) -> str:
    """Return safe editorial guidance without treating score as publication approval."""

    if prioridad == "alto" and estado_evidencia == "insuficiente":
        return "Prioridad alta: requiere investigación y no es publicable."
    return f"Evidencia: {estado_evidencia}. La prioridad no aprueba publicación."


def render_group_card(group: InboxGroup) -> None:
    """Render score, evidence, corroboration, and repetition as distinct facts."""

    group_date = _group_date(group)
    with st.container(border=True):
        st.subheader(group.titulo_representativo)
        st.caption(f"Tema: {group.tema} · Fecha más reciente: {group_date:%d/%m/%Y}")
        score, priority, evidence = st.columns(3)
        score.metric("Puntaje", f"{group.puntaje:.1f}")
        priority.metric("Prioridad", group.prioridad)
        evidence.metric("Estado de evidencia", group.estado_evidencia)
        articles, sources = st.columns(2)
        articles.metric("Artículos agrupados", group.n_noticias)
        sources.metric("Corroboración (fuentes distintas)", group.corroboracion)
        st.caption(
            f"Reglas: {group.version_reglas} · Componentes R/I/U/N/E: "
            f"{group.R:.1f}/{group.I:.1f}/{group.U:.1f}/{group.N:.1f}/{group.E:.1f}"
        )
        st.caption(f"Motivos: {group.motivos}")
        guidance = editorial_guidance(group.prioridad, group.estado_evidencia)
        if group.prioridad == "alto" and group.estado_evidencia == "insuficiente":
            st.warning(guidance)
        else:
            st.caption(guidance)
        if group.es_repeticion:
            st.warning("Repetición detectada: no aumenta la corroboración.")
        else:
            st.caption("Sin repetición detectada en este grupo.")


def main() -> None:
    """Render the Spanish editorial inbox and its explicit data states."""

    st.set_page_config(page_title="Bandeja editorial")
    st.title("Bandeja editorial")
    st.caption("Orden: mayor puntaje, luego urgencia (U) y finalmente identificador.")

    try:
        fingerprint = database_fingerprint(MOTOR_PATH, SIGNALS_PATH)
        topics, min_date, max_date = load_inbox_filter_options(
            str(MOTOR_PATH), str(SIGNALS_PATH), fingerprint
        )
    except ScoreUnavailableError:
        st.warning("Puntaje no disponible. Ejecute el motor de puntaje antes de consultar la bandeja.")
        return
    except (duckdb.Error, OSError):
        st.warning("Los datos no están disponibles. Ejecute el motor antes de consultar la bandeja.")
        return

    if min_date is None or max_date is None:
        st.info("No hay grupos disponibles para revisión.")
        return
    topic_column, start_column, end_column = st.columns(3)
    with topic_column:
        selected_topic = st.selectbox("Tema", ["Todos", *topics])
    with start_column:
        start_date = st.date_input("Desde", value=min_date, min_value=min_date, max_value=max_date)
    with end_column:
        end_date = st.date_input("Hasta", value=max_date, min_value=min_date, max_value=max_date)

    if start_date > end_date:
        st.warning("La fecha inicial debe ser anterior o igual a la fecha final.")
        return

    try:
        groups = load_inbox(
            str(MOTOR_PATH), str(SIGNALS_PATH), fingerprint,
            None if selected_topic == "Todos" else selected_topic, start_date, end_date,
        )
    except ScoreUnavailableError:
        st.warning("Puntaje no disponible. Ejecute el motor de puntaje antes de consultar la bandeja.")
        return

    if not groups:
        st.info("No hay grupos que coincidan con los filtros seleccionados.")
        return

    for group in groups:
        render_group_card(group)


if __name__ == "__main__":
    main()
