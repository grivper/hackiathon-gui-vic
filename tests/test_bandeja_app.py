from __future__ import annotations

from datetime import date, datetime

from app.app import (
    database_fingerprint,
    editorial_guidance,
    evidence_date_label,
    evidence_verification_guidance,
    render_group_chat,
    render_group_draft,
    render_official_context,
)
from app.data import GroupFicha, InboxGroup


_GROUP = InboxGroup(
    grupo_id="G-1",
    titulo_representativo="",
    n_noticias=1,
    n_procedencias=1,
    fecha_max=date(2026, 1, 1),
    corroboracion=1,
    es_repeticion=False,
    tema="otros",
    R=0, I=0, U=0, N=0, E=0, puntaje=0, prioridad="bajo",
    estado_evidencia="insuficiente", version_reglas="v0.3",
    motivos="", contexto_oficial=None, evento_usgs_id=None
)


def test_database_fingerprint_changes_when_either_database_changes(tmp_path):
    motor_path = tmp_path / "motor.duckdb"
    signals_path = tmp_path / "senales.duckdb"
    motor_path.write_bytes(b"motor-v1")
    signals_path.write_bytes(b"signals-v1")

    original = database_fingerprint(motor_path, signals_path)

    motor_path.write_bytes(b"motor-v2-with-a-different-size")
    after_motor_change = database_fingerprint(motor_path, signals_path)
    signals_path.write_bytes(b"signals-v2-with-a-different-size")
    after_signals_change = database_fingerprint(motor_path, signals_path)

    assert after_motor_change != original
    assert after_signals_change != after_motor_change


def test_high_priority_with_insufficient_evidence_requires_investigation():
    guidance = editorial_guidance("alto", "insuficiente")

    assert "requiere investigación" in guidance
    assert "no es publicable" in guidance


def test_evidence_date_label_keeps_missing_publication_date_unavailable():
    assert evidence_date_label(None) == "No disponible"
    assert evidence_date_label(datetime(2026, 1, 3, 14, 30)) == "03/01/2026"
    assert evidence_date_label(date(2026, 1, 4)) == "04/01/2026"


def test_insufficient_evidence_verification_guidance_requires_investigation():
    guidance = evidence_verification_guidance("insuficiente")

    assert "procedencias distintas" in guidance
    assert "requiere investigación" in guidance
    assert "no es publicable" in guidance


def test_render_official_context_avoids_rendering_when_missing(monkeypatch):
    from unittest.mock import Mock
    st_info = Mock()
    st_markdown = Mock()
    monkeypatch.setattr("app.app.st.info", st_info)
    monkeypatch.setattr("app.app.st.markdown", st_markdown)
    render_official_context(None, None)
    render_official_context("", "")
    st_info.assert_not_called()
    st_markdown.assert_not_called()


def test_render_official_context_displays_available_sources(monkeypatch):
    from unittest.mock import Mock

    st_info = Mock()
    st_markdown = Mock()
    monkeypatch.setattr("app.app.st.info", st_info)
    monkeypatch.setattr("app.app.st.markdown", st_markdown)
    render_official_context("PIB: 5%", "usgs-123")
    st_markdown.assert_any_call("**Contexto oficial (Banco Mundial / USGS)**")
    st_info.assert_any_call("**Indicadores Banco Mundial:** PIB: 5%")
    st_info.assert_any_call(
        "**Evento sísmico verificado (USGS):** [usgs-123](https://earthquake.usgs.gov/earthquakes/eventpage/usgs-123)"
    )


def _patch_draft_widgets(monkeypatch, *, selectbox_return="nuevo"):
    from unittest.mock import MagicMock, Mock

    widgets = {
        "expander": MagicMock(),
        "caption": Mock(),
        "markdown": Mock(),
        "info": Mock(),
        "warning": Mock(),
        "success": Mock(),
        "selectbox": Mock(return_value=selectbox_return),
        "popover": MagicMock(),
    }
    for name, mock in widgets.items():
        monkeypatch.setattr(f"app.app.st.{name}", mock)
    monkeypatch.setattr("app.app.st.session_state", {})
    return widgets


def test_render_group_draft_shows_an_honest_message_when_no_ficha_exists(monkeypatch):
    from unittest.mock import Mock

    widgets = _patch_draft_widgets(monkeypatch)
    monkeypatch.setattr("app.app.fetch_group_ficha", Mock(return_value=None))
    monkeypatch.setattr("app.app.persist_ficha_review_state", Mock())

    render_group_draft(_GROUP)

    widgets["info"].assert_any_call(
        "Borrador no generado para este grupo (ejecutar make generar)."
    )
    widgets["selectbox"].assert_not_called()


def test_render_group_draft_exposes_the_five_mandatory_states_for_a_real_response(monkeypatch):
    from unittest.mock import Mock

    widgets = _patch_draft_widgets(monkeypatch, selectbox_return="en revisión")
    ficha = GroupFicha(
        id_caso="G-1",
        estado_revision="en revisión",
        tipo_respuesta="respuesta",
        borrador="El evento ocurrió en enero.",
        citas=[("E-1", "titulo")],
        afirmaciones=["El evento ocurrió en enero."],
        motivo_abstencion=None,
        generado_en=datetime(2026, 1, 2, 9, 0),
    )
    monkeypatch.setattr("app.app.fetch_group_ficha", Mock(return_value=ficha))
    monkeypatch.setattr("app.app.persist_ficha_review_state", Mock())

    render_group_draft(_GROUP)

    widgets["selectbox"].assert_called_once()
    assert widgets["selectbox"].call_args[0][1] == [
        "nuevo",
        "en revisión",
        "requiere evidencia",
        "aprobado como borrador",
        "descartado"
    ]
    assert widgets["selectbox"].call_args.kwargs["index"] == 1
    widgets["markdown"].assert_any_call("El evento ocurrió en enero.")
    widgets["caption"].assert_any_call("Citas empleadas: E-1 · titulo")


def test_render_group_draft_renders_abstention_without_draft_text(monkeypatch):
    from unittest.mock import Mock

    widgets = _patch_draft_widgets(monkeypatch)
    ficha = GroupFicha(
        id_caso="G-1",
        estado_revision="nuevo",
        tipo_respuesta="abstencion",
        borrador=None,
        citas=[],
        afirmaciones=[],
        motivo_abstencion="No hay corroboración suficiente.",
        generado_en=datetime(2026, 1, 2),
    )
    monkeypatch.setattr("app.app.fetch_group_ficha", Mock(return_value=ficha))
    monkeypatch.setattr("app.app.persist_ficha_review_state", Mock())

    render_group_draft(_GROUP)

    assert not any(
        call.args and call.args[0] == "El evento ocurrió en enero." for call in widgets["markdown"].call_args_list
    )
    assert any(
        "No hay corroboración suficiente." in str(call) for call in widgets["caption"].call_args_list
    )


def test_render_group_draft_scopes_the_selectbox_key_to_the_generation_timestamp_so_regenerating_does_not_inherit_approval(monkeypatch):
    from unittest.mock import Mock

    widgets = _patch_draft_widgets(monkeypatch, selectbox_return="nuevo")
    approved = GroupFicha(
        id_caso="G-1", estado_revision="aprobado como borrador", tipo_respuesta="respuesta",
        borrador="v1", citas=[], afirmaciones=[], motivo_abstencion=None,
        generado_en=datetime(2026, 1, 1),
    )
    regenerated = GroupFicha(
        id_caso="G-1", estado_revision="nuevo", tipo_respuesta="respuesta",
        borrador="v2", citas=[], afirmaciones=[], motivo_abstencion=None,
        generado_en=datetime(2026, 1, 2),
    )
    fetch_mock = Mock(side_effect=[approved, regenerated])
    monkeypatch.setattr("app.app.fetch_group_ficha", fetch_mock)
    monkeypatch.setattr("app.app.persist_ficha_review_state", Mock())

    render_group_draft(_GROUP)
    first_call = widgets["selectbox"].call_args
    render_group_draft(_GROUP)
    second_call = widgets["selectbox"].call_args

    assert first_call.kwargs["key"] != second_call.kwargs["key"]
    assert first_call.kwargs["index"] == 3  # aprobado como borrador
    assert second_call.kwargs["index"] == 0  # nuevo: the new ficha never inherits the old approval


def test_render_group_draft_persists_the_review_state_when_the_editor_changes_it(monkeypatch):
    from unittest.mock import Mock

    widgets = _patch_draft_widgets(monkeypatch, selectbox_return="aprobado como borrador")
    ficha = GroupFicha(
        id_caso="G-1", estado_revision="nuevo", tipo_respuesta="respuesta",
        borrador="v1", citas=[], afirmaciones=[], motivo_abstencion=None,
        generado_en=datetime(2026, 1, 1),
    )
    monkeypatch.setattr("app.app.fetch_group_ficha", Mock(return_value=ficha))
    persist_mock = Mock()
    monkeypatch.setattr("app.app.persist_ficha_review_state", persist_mock)

    render_group_draft(_GROUP)

    persist_mock.assert_called_once()
    assert persist_mock.call_args.args[1:] == ("G-1", "aprobado como borrador")


def test_render_group_draft_does_not_persist_when_the_state_is_unchanged(monkeypatch):
    from unittest.mock import Mock

    _patch_draft_widgets(monkeypatch, selectbox_return="nuevo")
    ficha = GroupFicha(
        id_caso="G-1", estado_revision="nuevo", tipo_respuesta="respuesta",
        borrador="v1", citas=[], afirmaciones=[], motivo_abstencion=None,
        generado_en=datetime(2026, 1, 1),
    )
    monkeypatch.setattr("app.app.fetch_group_ficha", Mock(return_value=ficha))
    persist_mock = Mock()
    monkeypatch.setattr("app.app.persist_ficha_review_state", persist_mock)

    render_group_draft(_GROUP)

    persist_mock.assert_not_called()


def test_render_group_chat_initializes_session_state(monkeypatch):
    from unittest.mock import MagicMock, Mock

    st_expander = MagicMock()
    st_caption = Mock()
    st_warning = Mock()
    st_chat_input = Mock(return_value=None)
    session_state = {}

    monkeypatch.setattr("app.app.st.expander", st_expander)
    monkeypatch.setattr("app.app.st.caption", st_caption)
    monkeypatch.setattr("app.app.st.warning", st_warning)
    monkeypatch.setattr("app.app.st.chat_input", st_chat_input)
    monkeypatch.setattr("app.app.st.session_state", session_state)

    render_group_chat(_GROUP)

    assert "chat_G-1" in session_state
    assert session_state["chat_G-1"] == []
    st_chat_input.assert_called_once()
    st_warning.assert_any_call(
        "Respuesta simulada: aún no usa el LLM ni la evidencia real (pendiente TAR-020/TAR-028)."
    )
