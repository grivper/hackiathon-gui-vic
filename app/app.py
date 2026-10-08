"""Streamlit entry point for the editorial priority inbox."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import duckdb
import streamlit as st

from app.data import (
    EvidenceRow,
    InboxGroup,
    ScoreUnavailableError,
    ask_group_question,
    fetch_group_evidence,
    fetch_inbox_filter_options,
    fetch_inbox_groups,
    generate_group_draft,
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
def load_group_evidence(
    motor_path: str,
    signals_path: str,
    database_identity: tuple[tuple[int, int], tuple[int, int]],
    grupo_id: str,
) -> list[EvidenceRow]:
    """Cache read-only group evidence until either database file changes."""

    return fetch_group_evidence(motor_path, signals_path, grupo_id)


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


def evidence_date_label(value: date | datetime | None) -> str:
    """Format source dates without substituting one metadata field for another."""

    if value is None:
        return "No disponible"
    return value.strftime("%d/%m/%Y")


def evidence_verification_guidance(estado_evidencia: str) -> str:
    """State the remaining editorial verification without approving publication."""

    if estado_evidencia == "insuficiente":
        return (
            "Por verificar: confirme el hecho con procedencias distintas; "
            "requiere investigación y no es publicable."
        )
    return (
        "Por verificar: confirme atribución, contexto y vigencia antes de publicar; "
        "la evidencia no sustituye la verificación editorial."
    )


def render_official_context(contexto: str | None, usgs_id: str | None) -> None:
    """Render the official context panel without conflating history with breaking news."""

    if not contexto and not usgs_id:
        return

    st.markdown("---")
    st.markdown("**Contexto oficial (Banco Mundial / USGS)**")
    st.caption("Esta sección provee una línea base histórica u oficial y no debe confundirse con la noticia en curso.")

    if usgs_id:
        url = f"https://earthquake.usgs.gov/earthquakes/eventpage/{usgs_id}"
        st.info(f"**Evento sísmico verificado (USGS):** [{usgs_id}]({url})")

    if contexto:
        st.info(f"**Indicadores Banco Mundial:** {contexto}")


def render_group_evidence(group: InboxGroup, evidence_rows: list[EvidenceRow]) -> None:
    """Render read-only member metadata, keeping corroboration separate from volume."""

    with st.expander("Detalle de evidencia", expanded=False):
        st.caption(
            f"{group.n_noticias} artículos agrupados. La corroboración considera "
            f"{group.corroboracion} procedencias distintas, no repeticiones del mismo origen."
        )
        st.info(evidence_verification_guidance(group.estado_evidencia))
        if not evidence_rows:
            st.caption("No hay miembros de evidencia disponibles para este grupo.")
            return

        for row in evidence_rows:
            st.markdown(f"**{row.titulo or 'Titular no disponible'}**")
            if row.url:
                st.link_button("Abrir fuente", row.url)
            st.caption(
                f"Medio: {row.medio or 'No disponible'} · "
                f"Procedencia: {row.procedencia or 'No disponible'}"
            )
            st.caption(
                "Fecha de publicación/original: "
                f"{evidence_date_label(row.fecha_publicacion)} · "
                f"Fecha de detección: {evidence_date_label(row.fecha_deteccion)}"
            )
            if row.similitud_al_centroide is not None:
                st.caption(
                    "Similitud con el grupo: "
                    f"{row.similitud_al_centroide:.0%} (referencia para revisar la agrupación)."
                )


def render_group_chat(group: InboxGroup) -> None:
    """Render a chat interface for cited CU-04 queries per group."""

    with st.expander("Consulta citada (IA)", expanded=False):
        st.caption("Consultá sobre este grupo. La IA responderá basándose **solo** en la evidencia.")

        chat_key = f"chat_{group.grupo_id}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []

        for msg in st.session_state[chat_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("citas"):
                    st.caption(f"Citas: {', '.join(msg['citas'])}")

        if question := st.chat_input("Escribí tu consulta acá...", key=f"input_{group.grupo_id}"):
            # Immediate render of user question
            st.session_state[chat_key].append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)

            # Mock LLM generation
            with st.spinner("Buscando en la evidencia..."):
                response = ask_group_question(group.grupo_id, question)

            msg_data = {
                "role": "assistant",
                "content": response.respuesta,
                "citas": response.citas
            }
            st.session_state[chat_key].append(msg_data)

            with st.chat_message("assistant"):
                st.markdown(response.respuesta)
                if response.abstencion:
                    st.warning("Abstención: La respuesta puede estar limitada por falta de datos.")
                if response.citas:
                    st.caption(f"Citas: {', '.join(response.citas)}")


def render_group_draft(group: InboxGroup) -> None:
    """Render an editorial draft interface with mandatory review states."""

    with st.expander("Borrador y revisión (IA)", expanded=False):
        st.caption(
            "Generá un borrador citable basado exclusivamente en la evidencia del grupo. "
            "Aprobar el borrador no lo publica automáticamente."
        )

        draft_key = f"draft_{group.grupo_id}"
        state_key = f"draft_state_{group.grupo_id}"

        if st.button("Generar borrador", key=f"btn_draft_{group.grupo_id}"):
            with st.spinner("Redactando borrador con citas..."):
                response = generate_group_draft(group.grupo_id)
                st.session_state[draft_key] = response
                st.session_state[state_key] = response.estado_revision

        if draft_key in st.session_state:
            draft = st.session_state[draft_key]

            st.markdown(draft.borrador)
            if draft.afirmaciones:
                with st.popover("Ver afirmaciones base"):
                    for a in draft.afirmaciones:
                        st.markdown(f"- {a}")
            if draft.citas:
                st.caption(f"Citas empleadas: {', '.join(draft.citas)}")

            st.markdown("---")
            st.markdown("**Revisión editorial**")
            current_state = st.session_state.get(state_key, "nuevo")

            # The exact 5 states mandated by the brief
            valid_states = [
                "nuevo",
                "en revisión",
                "requiere evidencia",
                "aprobado como borrador",
                "descartado"
            ]
            try:
                index = valid_states.index(current_state)
            except ValueError:
                index = 0

            new_state = st.selectbox(
                "Estado del borrador",
                valid_states,
                index=index,
                key=f"select_{group.grupo_id}"
            )
            st.session_state[state_key] = new_state

            if new_state == "aprobado como borrador":
                st.success("Borrador aprobado. (Nota: Esto no publica el artículo en el CMS).")
            elif new_state == "requiere evidencia":
                st.warning("Se requiere más investigación o evidencia de otras fuentes.")


def render_group_card(group: InboxGroup, evidence_rows: list[EvidenceRow]) -> None:
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
        sources.metric("Corroboración (procedencias distintas)", group.corroboracion)
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
        render_official_context(group.contexto_oficial, group.evento_usgs_id)
        render_group_evidence(group, evidence_rows)
        render_group_chat(group)
        render_group_draft(group)


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
        try:
            evidence_rows = load_group_evidence(
                str(MOTOR_PATH), str(SIGNALS_PATH), fingerprint, group.grupo_id
            )
        except duckdb.Error:
            evidence_rows = []
        render_group_card(group, evidence_rows)


if __name__ == "__main__":
    main()
