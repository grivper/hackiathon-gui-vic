"""Streamlit entry point for the editorial priority inbox."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import duckdb
import streamlit as st

if __package__:
    from . import data as data_module
    from . import estilos, generacion
else:
    import data as data_module
    import estilos
    import generacion

VALID_REVIEW_STATES = data_module.VALID_REVIEW_STATES
EvidenceRow = data_module.EvidenceRow
GroupFicha = data_module.GroupFicha
InboxGroup = data_module.InboxGroup
ScoreUnavailableError = data_module.ScoreUnavailableError
ask_group_question = data_module.ask_group_question
suggest_questions = data_module.suggest_questions
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

    st.markdown("**Contexto oficial (Banco Mundial / USGS)**")
    st.caption("Esta sección provee una línea base histórica u oficial y no debe confundirse con la noticia en curso.")

    if usgs_id:
        url = f"https://earthquake.usgs.gov/earthquakes/eventpage/{usgs_id}"
        st.markdown(
            estilos.info_html(
                "Evento sísmico verificado (USGS):", "", href=url, link_text=usgs_id
            ),
            unsafe_allow_html=True,
        )

    if contexto:
        st.markdown(
            estilos.info_html("Indicadores Banco Mundial:", contexto),
            unsafe_allow_html=True,
        )


def render_group_evidence(group: InboxGroup, evidence_rows: list[EvidenceRow]) -> None:
    """Render read-only member metadata, keeping corroboration separate from volume."""

    with st.container(key=f"sec-evidencia-{group.grupo_id}"):
        st.markdown(estilos.heading_html("Evidencia y procedencias"), unsafe_allow_html=True)
        st.markdown(
            estilos.chips_html(
                [
                    (f"{group.n_noticias} artículos agrupados", ""),
                    (
                        f"{group.corroboracion} procedencias distintas (no repeticiones)",
                        "",
                    ),
                ]
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            estilos.note_html(
                "Basado únicamente en titular/metadatos. "
                "La confirmación editorial sigue pendiente."
            ),
            unsafe_allow_html=True,
        )
        guidance = evidence_verification_guidance(group.estado_evidencia)
        label, _, rest = guidance.partition(":")
        st.markdown(
            estilos.info_html(f"{label}:", rest.strip() and f" {rest.strip()}"),
            unsafe_allow_html=True,
        )
        if not evidence_rows:
            st.caption("No hay miembros de evidencia disponibles para este grupo.")
            return

        for row in evidence_rows:
            evidence_box = st.container(key=f"evid-{group.grupo_id}-{row.id_noticia}")
            evidence_box.markdown(
                estilos.evidence_head_html(
                    row.titulo or "Titular no disponible",
                    str(row.id_noticia),
                    "titulo" if row.titulo else None,
                ),
                unsafe_allow_html=True,
            )
            if row.url:
                evidence_box.link_button("Abrir fuente original", row.url)
            details = [
                ("Medio/origen", row.medio or "No disponible"),
                ("Procedencia", row.procedencia or "No disponible"),
                (
                    "Fecha de publicación/original",
                    evidence_date_label(row.fecha_publicacion),
                ),
                ("Fecha de detección", evidence_date_label(row.fecha_deteccion)),
            ]
            if row.similitud_al_centroide is not None:
                details.append(
                    ("Similitud con el grupo", f"{row.similitud_al_centroide:.0%}")
                )
            evidence_box.markdown(
                estilos.evidence_kv_html(details), unsafe_allow_html=True
            )
            if row.similitud_al_centroide is not None:
                evidence_box.caption(
                    "La similitud es una referencia para revisar la agrupación."
                )


CHAT_HISTORY_HEIGHT = 380  # px; the history always scrolls inside a box of this height


def render_group_chat(group: InboxGroup) -> None:
    """Render a chat interface for cited CU-04 queries per group."""

    with st.expander("Consulta sobre evidencia validada", expanded=True):
        st.caption(
            "La respuesta es extractiva: solo recupera afirmaciones y citas "
            "validadas de la ficha."
        )

        chat_key = f"chat_{group.grupo_id}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []

        # The history lives in a container created before the input, so new
        # messages are drawn above the input instead of below it.
        pending_key = f"pregunta_pendiente_{group.grupo_id}"
        history = st.container(height=CHAT_HISTORY_HEIGHT)
        typed = st.chat_input("Escribí tu consulta acá...", key=f"input_{group.grupo_id}")
        question = typed or st.session_state.pop(pending_key, None)

        with history:
            if not st.session_state[chat_key] and not question:
                ficha = fetch_group_ficha(
                    MOTOR_PATH, SIGNALS_PATH, group.grupo_id, fichas_path=FICHAS_PATH
                )
                examples = suggest_questions(ficha)
                if examples:
                    st.caption("Ejemplos de preguntas que se pueden hacer:")
                    for number, example in enumerate(examples):
                        if st.button(example, key=f"ejemplo_{group.grupo_id}_{number}"):
                            st.session_state[pending_key] = example
                            st.rerun()
                else:
                    st.caption(
                        "Todavía no hay borrador para este grupo: el chat solo responde "
                        "sobre fichas generadas. Genere el borrador más abajo."
                    )
            for msg in st.session_state[chat_key]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg.get("citas"):
                        st.caption(f"Citas: {', '.join(msg['citas'])}")

            if question:
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

                st.session_state[chat_key].append(
                    {
                        "role": "assistant",
                        "content": response.respuesta,
                        "citas": response.citas,
                    }
                )

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


def render_generate_draft(group: InboxGroup) -> None:
    """Button that generates the draft of THIS group only, when the local LLM is available."""

    available, reason = generacion.estado_ollama()
    clicked = st.button(
        "Generar borrador con IA", key=f"generar_{group.grupo_id}", disabled=not available
    )
    if not available:
        st.markdown(estilos.empty_note_html(reason), unsafe_allow_html=True)
        return
    st.markdown(
        estilos.empty_note_html(
            "Usa el modelo local (sin enviar datos fuera). Tarda unos 20 segundos y solo "
            "genera este grupo."
        ),
        unsafe_allow_html=True,
    )
    if not clicked:
        return
    with st.spinner("Generando el borrador con evidencia citada…"):
        result = generacion.generar_borrador(
            group.grupo_id, MOTOR_PATH, SIGNALS_PATH, FICHAS_PATH
        )
    if result.status == "generada":
        st.rerun()
    elif result.status == "ya_revisada":
        st.warning(
            "Este borrador ya fue revisado por una persona y no se sobrescribe. "
            f"{result.detail}"
        )
    else:
        st.error(
            "El modelo no devolvió una salida utilizable; no se guardó nada. "
            f"Puede reintentar. {result.detail}"
        )


def render_group_draft(group: InboxGroup) -> None:
    """Render the real TAR-009 editorial draft with mandatory review states.

    Reads a fresh ficha on every render (not cached): the selectbox key is
    scoped to the ficha's own generation timestamp, so a regenerated ficha
    for the same group never inherits a previous approval left over in the
    widget's session state.
    """

    with st.expander("Paquete generado y revisión humana", expanded=True):
        st.markdown(
            estilos.aviso_html(
                "Información generada: el borrador no equivale a información verificada "
                "ni autoriza publicación.",
                "Aprobar el borrador no lo publica automáticamente.",
            ),
            unsafe_allow_html=True,
        )

        ficha = fetch_group_ficha(
            MOTOR_PATH, SIGNALS_PATH, group.grupo_id, fichas_path=FICHAS_PATH
        )
        if ficha is None:
            with st.container(key=f"vacio_{group.grupo_id}"):
                st.markdown(estilos.empty_head_html(), unsafe_allow_html=True)
                render_generate_draft(group)
            return

        with st.container(key=f"borrador_{group.grupo_id}"):
            _render_draft_body(group, ficha)


def _render_draft_body(group: InboxGroup, ficha: GroupFicha) -> None:
    """The generated draft, its citations and the mandatory review state."""

    if ficha.tipo_respuesta == "abstencion":
        st.warning("Abstención: no hay evidencia suficiente para redactar un borrador.")
        if ficha.borrador:
            st.markdown(ficha.borrador)
        if ficha.motivo_abstencion:
            st.caption(f"Motivo: {ficha.motivo_abstencion}")
    else:
        if ficha.tipo_respuesta == "contradiccion":
            st.warning("Contradicción detectada entre las fuentes citadas.")
        st.caption("Borrador citable basado exclusivamente en la evidencia del grupo.")
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
        key=f"select_{group.grupo_id}_{ficha.generado_en}",
    )

    if new_state != ficha.estado_revision:
        persist_ficha_review_state(MOTOR_PATH, group.grupo_id, new_state)

    if new_state == "aprobado como borrador":
        st.success("Borrador aprobado como borrador: ni publica ni autoriza su publicación.")
    elif new_state == "requiere evidencia":
        st.warning("Se requiere más investigación o evidencia de otras fuentes.")


def _display_chips(group: InboxGroup) -> list[tuple[str, str]]:
    evidence_kind = "warn" if group.estado_evidencia == "insuficiente" else ""
    return [
        (f"Evidencia {group.estado_evidencia} · {group.n_noticias} registros", evidence_kind),
        (f"{group.corroboracion} procedencias distintas", ""),
    ]


def render_bandeja_row(group: InboxGroup, rank: int) -> None:
    """One ranked inbox row with the button that opens its ficha."""

    with st.container(key=f"row-{group.grupo_id}"):
        content, score, action = st.columns([6, 2, 1.5], vertical_alignment="center")
        content.markdown(
            estilos.row_content_html(
                rank=rank,
                tema=group.tema,
                fecha=evidence_date_label(_group_date(group)),
                titulo=group.titulo_representativo,
                chips=_display_chips(group),
            ),
            unsafe_allow_html=True,
        )
        score.markdown(estilos.score_block_html(group.puntaje), unsafe_allow_html=True)
        if action.button("Abrir ficha →", key=f"abrir_{group.grupo_id}"):
            st.session_state["ficha_id"] = group.grupo_id
            st.rerun()


def render_ficha(group: InboxGroup, evidence_rows: list[EvidenceRow]) -> None:
    """Full-page ficha: score, evidence, official context, query and draft."""

    st.markdown(
        estilos.ficha_header_html(group.tema, group.grupo_id, group.titulo_representativo),
        unsafe_allow_html=True,
    )
    main_column, side_column = st.columns([2, 1], gap="large")
    with main_column:
        if group.estado_evidencia == "insuficiente":
            st.markdown(
                estilos.alert_html(
                    f"Prioridad {group.prioridad.capitalize()}: requiere investigación",
                    "No es publicable.",
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                estilos.alert_html(
                    editorial_guidance(group.prioridad, group.estado_evidencia)
                ),
                unsafe_allow_html=True,
            )
        repetition = (
            "Repetición detectada: no aumenta la corroboración."
            if group.es_repeticion
            else "Sin repetición detectada en este grupo."
        )
        st.markdown(
            estilos.resumen_reporte_html(group.motivos, repetition),
            unsafe_allow_html=True,
        )
        render_group_evidence(group, evidence_rows)
        with st.container(key=f"sec-contexto-{group.grupo_id}"):
            if group.contexto_oficial or group.evento_usgs_id:
                render_official_context(group.contexto_oficial, group.evento_usgs_id)
            else:
                st.markdown(estilos.heading_html("Contexto oficial"), unsafe_allow_html=True)
                st.markdown(
                    '<div class="muted">Sin contexto oficial disponible para este registro.</div>',
                    unsafe_allow_html=True,
                )
        with st.container(key=f"sec-consulta-{group.grupo_id}"):
            st.markdown(estilos.heading_html("Consulta"), unsafe_allow_html=True)
            render_group_chat(group)
            render_group_draft(group)
        if st.button("← Volver a la bandeja", key="volver-abajo"):
            st.session_state["ficha_id"] = None
            st.rerun()
    with side_column:
        st.markdown(
            estilos.aside_html(
                puntaje=group.puntaje,
                prioridad=group.prioridad,
                estado_evidencia=group.estado_evidencia,
                version_reglas=group.version_reglas,
            ),
            unsafe_allow_html=True,
        )


FILTER_KEYS = ("filtro_tema", "filtro_desde", "filtro_hasta")


def main() -> None:
    """Render the Spanish editorial inbox (or one ficha) and its data states."""

    st.set_page_config(page_title="Bandeja editorial", layout="wide")
    st.markdown(estilos.CSS, unsafe_allow_html=True)
    # Widgets that are not rendered on a run lose their state; keep the filters
    # alive while the ficha page is open so "Volver" restores them.
    for key in FILTER_KEYS:
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]
    ficha_id = st.session_state.get("ficha_id")
    hero_slot = st.empty()
    if not ficha_id:
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

    if ficha_id:
        # Look the group up with the SAME filters as the inbox: it is capped at 50 rows
        # per query, so a group listed under a filter may not be in the unfiltered top 50.
        saved_topic = st.session_state.get("filtro_tema", "Todos")
        try:
            every_group = load_inbox(
                str(MOTOR_PATH), str(SIGNALS_PATH), fingerprint,
                None if saved_topic == "Todos" else saved_topic,
                st.session_state.get("filtro_desde", min_date),
                st.session_state.get("filtro_hasta", max_date),
            )
        except ScoreUnavailableError:
            st.warning("Puntaje no disponible. Ejecute el motor de puntaje antes de consultar la bandeja.")
            return
        selected = next((g for g in every_group if g.grupo_id == ficha_id), None)
        if selected is not None:
            try:
                evidence_rows = load_group_evidence(
                    str(MOTOR_PATH), str(SIGNALS_PATH), fingerprint, selected.grupo_id
                )
            except duckdb.Error:
                evidence_rows = []
                st.warning("No se pudo cargar la evidencia de este grupo.")
            render_ficha(selected, evidence_rows)
            return
        st.session_state["ficha_id"] = None  # the record no longer exists
        hero_slot.markdown(estilos.hero_html(0, 0, 0), unsafe_allow_html=True)

    with st.container(key="filtros"):
        topic_column, start_column, end_column = st.columns([2, 1, 1])
        with topic_column:
            selected_topic = st.selectbox(
                "Tema",
                ["Todos", *topics],
                key="filtro_tema",
                format_func=lambda topic: topic if topic == "Todos" else estilos.tema_label(topic),
            )
        with start_column:
            start_date = st.date_input(
                "Desde", value=min_date, min_value=min_date, max_value=max_date, key="filtro_desde"
            )
        with end_column:
            end_date = st.date_input(
                "Hasta", value=max_date, min_value=min_date, max_value=max_date, key="filtro_hasta"
            )

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
        estilos.title_row_html(
            "Bandeja de revisión",
            "Orden: mayor puntaje, luego urgencia (U) y finalmente identificador.",
        ),
        unsafe_allow_html=True,
    )
    for rank, group in enumerate(groups, 1):
        render_bandeja_row(group, rank)


if __name__ == "__main__":
    main()
