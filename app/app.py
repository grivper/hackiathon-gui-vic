"""Streamlit entry point for the editorial priority inbox."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import duckdb
import streamlit as st

if __package__:
    from . import data as data_module
    from . import estilos
else:
    import data as data_module
    import estilos

VALID_REVIEW_STATES = data_module.VALID_REVIEW_STATES
EvidenceRow = data_module.EvidenceRow
InboxGroup = data_module.InboxGroup
ScoreUnavailableError = data_module.ScoreUnavailableError
ask_group_question = data_module.ask_group_question
fetch_group_evidence = data_module.fetch_group_evidence
fetch_group_ficha = data_module.fetch_group_ficha
fetch_inbox_filter_options = data_module.fetch_inbox_filter_options
fetch_inbox_groups = data_module.fetch_inbox_groups
persist_ficha_review_state = data_module.persist_ficha_review_state


ROOT_DIR = Path(__file__).resolve().parents[1]
MOTOR_PATH = ROOT_DIR / "data" / "motor.duckdb"
SIGNALS_PATH = ROOT_DIR / "data" / "senales.duckdb"
FICHAS_PATH = ROOT_DIR / "data" / "fichas.jsonl"


def _file_fingerprint(path: str | Path) -> tuple[int, int]:
    """Return a stable cache identity, including for an absent optional file."""

    try:
        stat = Path(path).stat()
    except FileNotFoundError:
        return (-1, -1)
    return (stat.st_mtime_ns, stat.st_size)


def database_fingerprint(
    motor_path: str | Path, signals_path: str | Path, fichas_path: str | Path
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    """Return a read-only cache identity for DuckDB files and JSONL fichas."""

    return (
        _file_fingerprint(motor_path),
        _file_fingerprint(signals_path),
        _file_fingerprint(fichas_path),
    )


@st.cache_data
def load_inbox_filter_options(
    motor_path: str,
    signals_path: str,
    database_identity: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
) -> tuple[list[str], date | None, date | None]:
    """Cache uncapped filter choices until either database file changes."""

    return fetch_inbox_filter_options(motor_path, signals_path)


@st.cache_data
def load_group_evidence(
    motor_path: str,
    signals_path: str,
    database_identity: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
    grupo_id: str,
) -> list[EvidenceRow]:
    """Cache read-only group evidence until either database file changes."""

    return fetch_group_evidence(motor_path, signals_path, grupo_id)


@st.cache_data
def load_inbox(
    motor_path: str,
    signals_path: str,
    database_identity: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
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

    if estado_evidencia == "insuficiente":
        return (
            f"Prioridad {prioridad}: requiere investigación y no es publicable."
        )
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
            st.caption(f"ID de evidencia: {row.id_noticia}")
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

    with st.expander("Consulta sobre evidencia validada", expanded=False):
        st.caption(
            "La respuesta es extractiva: solo recupera afirmaciones y citas "
            "validadas de la ficha."
        )

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

            with st.spinner("Buscando en la evidencia validada..."):
                response = ask_group_question(
                    group.grupo_id,
                    question,
                    motor_path=MOTOR_PATH,
                    signals_path=SIGNALS_PATH,
                    fichas_path=FICHAS_PATH,
                )

            msg_data = {
                "role": "assistant",
                "content": response.respuesta,
                "citas": response.citas
            }
            st.session_state[chat_key].append(msg_data)

            with st.chat_message("assistant"):
                st.markdown(response.respuesta)
                if response.abstencion:
                    st.warning(
                        "Abstención: no hay evidencia validada suficiente para responder "
                        "esta consulta; requiere investigación."
                    )
                else:
                    if response.contradiccion:
                        st.warning(
                            "Contradicción detectada entre las fuentes citadas; "
                            "revisión pendiente."
                        )
                    if response.citas:
                        st.caption(f"Citas verificadas: {', '.join(response.citas)}")


def render_group_draft(group: InboxGroup) -> None:
    """Render the real TAR-009 editorial draft with mandatory review states.

    Reads a fresh ficha on every render (not cached): the selectbox key is
    scoped to the ficha's own generation timestamp, so a regenerated ficha
    for the same group never inherits a previous approval left over in the
    widget's session state.
    """

    with st.expander("Borrador y revisión (IA)", expanded=False):
        st.caption("Aprobar el borrador no lo publica automáticamente.")

        ficha = fetch_group_ficha(
            MOTOR_PATH, SIGNALS_PATH, group.grupo_id, fichas_path=FICHAS_PATH
        )
        if ficha is None:
            st.info("Borrador no generado para este grupo (ejecutar make generar).")
            return

        if ficha.tipo_respuesta == "abstencion":
            st.warning("Abstención: no hay evidencia suficiente para redactar un borrador.")
            if ficha.borrador:
                st.markdown(ficha.borrador)
            if ficha.motivo_abstencion:
                st.caption(f"Motivo: {ficha.motivo_abstencion}")
        else:
            if ficha.tipo_respuesta == "contradiccion":
                st.warning("Contradicción detectada entre las fuentes citadas.")
            st.caption(
                "Borrador citable basado exclusivamente en la evidencia del grupo."
            )
            st.markdown(ficha.borrador or "")
            if ficha.afirmaciones:
                with st.popover("Ver afirmaciones base"):
                    for a in ficha.afirmaciones:
                        st.markdown(f"- {a}")
            if ficha.citas:
                citas_label = ", ".join(
                    f"{id_evidencia} · {campo}" for id_evidencia, campo in ficha.citas
                )
                st.caption(f"Citas empleadas: {citas_label}")

        st.markdown("---")
        st.markdown("**Revisión editorial**")
        if not ficha.persistable:
            st.warning(
                "Ficha JSONL de solo lectura: el estado no se puede guardar. "
                "La persistencia requiere una ficha generada en DuckDB."
            )
            return

        try:
            index = VALID_REVIEW_STATES.index(ficha.estado_revision)
        except ValueError:
            index = 0

        new_state = st.selectbox(
            "Estado del borrador",
            list(VALID_REVIEW_STATES),
            index=index,
            key=f"select_{group.grupo_id}_{ficha.generado_en}"
        )

        if new_state != ficha.estado_revision:
            persist_ficha_review_state(MOTOR_PATH, group.grupo_id, new_state)

        if new_state == "aprobado como borrador":
            st.success(
                "Borrador aprobado como borrador: ni publica ni autoriza su publicación."
            )
        elif new_state == "requiere evidencia":
            st.warning("Se requiere más investigación o evidencia de otras fuentes.")


def render_group_card(group: InboxGroup, evidence_rows: list[EvidenceRow], rank: int = 1) -> None:
    """Render score, evidence, corroboration, and repetition as distinct facts."""

    group_date = _group_date(group)
    with st.container(border=True):
        priority_kind = "danger" if group.prioridad.lower() == "alto" else ""
        evidence_kind = "warn" if group.estado_evidencia == "insuficiente" else ""
        st.markdown(
            estilos.score_card_html(
                rank=rank,
                tema=group.tema,
                fecha=evidence_date_label(group_date),
                titulo=group.titulo_representativo,
                chips=[
                    (f"Prioridad {group.prioridad}", priority_kind),
                    (f"Evidencia {group.estado_evidencia}", evidence_kind),
                    (f"{group.n_noticias} artículos agrupados", ""),
                    (f"{group.corroboracion} procedencias distintas (corroboración)", ""),
                ],
                puntaje=group.puntaje,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            estilos.component_bars_html(
                {"R": group.R, "I": group.I, "U": group.U, "N": group.N, "E": group.E}
            ),
            unsafe_allow_html=True,
        )
        st.caption(
            f"Reglas: {group.version_reglas} · Componentes R/I/U/N/E: "
            f"{group.R:.1f}/{group.I:.1f}/{group.U:.1f}/{group.N:.1f}/{group.E:.1f}"
        )
        st.caption(f"Motivos: {group.motivos}")
        guidance = editorial_guidance(group.prioridad, group.estado_evidencia)
        if group.estado_evidencia == "insuficiente":
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

    st.set_page_config(page_title="Bandeja editorial", layout="wide")
    st.markdown(estilos.CSS, unsafe_allow_html=True)
    hero_slot = st.empty()
    hero_slot.markdown(estilos.hero_html(0, 0, 0), unsafe_allow_html=True)

    try:
        fingerprint = database_fingerprint(MOTOR_PATH, SIGNALS_PATH, FICHAS_PATH)
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

    hero_slot.markdown(
        estilos.hero_html(
            len(groups),
            sum(g.prioridad.lower() == "alto" for g in groups),
            sum(g.estado_evidencia == "insuficiente" for g in groups),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        estilos.section_title_html(
            "Bandeja editorial",
            "Orden: mayor puntaje, luego urgencia (U) y finalmente identificador.",
        ),
        unsafe_allow_html=True,
    )
    for rank, group in enumerate(groups, 1):
        try:
            evidence_rows = load_group_evidence(
                str(MOTOR_PATH), str(SIGNALS_PATH), fingerprint, group.grupo_id
            )
        except duckdb.Error:
            evidence_rows = []
            st.warning("No se pudo cargar la evidencia de este grupo.")
        render_group_card(group, evidence_rows, rank)


if __name__ == "__main__":
    main()
