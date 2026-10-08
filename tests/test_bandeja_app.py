from __future__ import annotations

import importlib.util
import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

import app.app as app_module
from app.app import (
    database_fingerprint,
    editorial_guidance,
    evidence_date_label,
    evidence_verification_guidance,
    render_group_chat,
    render_group_draft,
    render_official_context,
)
from app.data import ChatResponse, GroupFicha, InboxGroup


def test_script_mode_import_loads_sibling_data_without_running_main(monkeypatch):
    app_path = Path(__file__).parents[1] / "app" / "app.py"
    repo_root = app_path.parents[1].resolve()
    script_paths = [
        str(app_path.parent),
        *(path for path in sys.path if path and Path(path).resolve() != repo_root),
    ]
    monkeypatch.setattr(sys, "path", script_paths)
    monkeypatch.delitem(sys.modules, "app", raising=False)
    monkeypatch.delitem(sys.modules, "app.data", raising=False)
    monkeypatch.delitem(sys.modules, "data", raising=False)
    spec = importlib.util.spec_from_file_location("streamlit_script", app_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.delitem(sys.modules, "data", raising=False)

    assert module.__package__ == ""
    assert module.fetch_inbox_groups.__module__ == "data"


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


def test_database_fingerprint_changes_when_any_data_source_changes_and_handles_missing_jsonl(tmp_path):
    motor_path = tmp_path / "motor.duckdb"
    signals_path = tmp_path / "senales.duckdb"
    fichas_path = tmp_path / "fichas.jsonl"
    motor_path.write_bytes(b"motor-v1")
    signals_path.write_bytes(b"signals-v1")

    missing = database_fingerprint(motor_path, signals_path, fichas_path)
    assert database_fingerprint(motor_path, signals_path, fichas_path) == missing

    fichas_path.write_text('{"id_caso": "G-1"}\n', encoding="utf-8")
    with_fichas = database_fingerprint(motor_path, signals_path, fichas_path)
    fichas_path.write_text('{"id_caso": "G-1", "updated": true}\n', encoding="utf-8")
    after_fichas_change = database_fingerprint(motor_path, signals_path, fichas_path)

    assert with_fichas != missing
    assert after_fichas_change != with_fichas


@pytest.mark.parametrize("prioridad", ["bajo", "medio", "alto"])
def test_insufficient_evidence_always_requires_investigation_and_is_not_publishable(prioridad):
    guidance = editorial_guidance(prioridad, "insuficiente")

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
    st_info.assert_not_called()
    rendered = " ".join(str(call.args[0]) for call in st_markdown.call_args_list)
    assert "Indicadores Banco Mundial:" in rendered and "PIB: 5%" in rendered
    assert "Evento sísmico verificado (USGS):" in rendered
    assert "https://earthquake.usgs.gov/earthquakes/eventpage/usgs-123" in rendered


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

    widgets["info"].assert_not_called()
    rendered = " ".join(str(call.args[0]) for call in widgets["markdown"].call_args_list)
    assert "Borrador no generado para este grupo (ejecutar <code>make generar</code>)." in rendered
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


def test_render_group_draft_renders_an_abstention_safe_draft_and_warning(monkeypatch):
    from unittest.mock import Mock

    widgets = _patch_draft_widgets(monkeypatch)
    ficha = GroupFicha(
        id_caso="G-1",
        estado_revision="nuevo",
        tipo_respuesta="abstencion",
        borrador="No se pudo verificar el hecho con la evidencia disponible.",
        citas=[],
        afirmaciones=[],
        motivo_abstencion="No hay corroboración suficiente.",
        generado_en=datetime(2026, 1, 2),
    )
    monkeypatch.setattr("app.app.fetch_group_ficha", Mock(return_value=ficha))
    monkeypatch.setattr("app.app.persist_ficha_review_state", Mock())

    render_group_draft(_GROUP)

    widgets["markdown"].assert_any_call(
        "No se pudo verificar el hecho con la evidencia disponible."
    )
    assert any("Abstención:" in str(call) for call in widgets["warning"].call_args_list)
    assert any(
        "No hay corroboración suficiente." in str(call) for call in widgets["caption"].call_args_list
    )


def test_render_group_draft_jsonl_fallback_is_read_only_without_selectbox_or_persistence(monkeypatch):
    widgets = _patch_draft_widgets(monkeypatch)
    ficha = GroupFicha(
        id_caso="G-1", estado_revision="nuevo", tipo_respuesta="respuesta",
        borrador="Ficha de respaldo.", citas=[], afirmaciones=[], motivo_abstencion=None,
        generado_en=None, source="jsonl", persistable=False,
    )
    monkeypatch.setattr("app.app.fetch_group_ficha", Mock(return_value=ficha))
    persist_mock = Mock()
    monkeypatch.setattr("app.app.persist_ficha_review_state", persist_mock)

    render_group_draft(_GROUP)

    widgets["selectbox"].assert_not_called()
    persist_mock.assert_not_called()
    assert any("solo lectura" in str(call).lower() for call in widgets["warning"].call_args_list)


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

    _patch_draft_widgets(monkeypatch, selectbox_return="aprobado como borrador")
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


def test_render_group_draft_approved_warning_does_not_authorize_publication(monkeypatch):
    widgets = _patch_draft_widgets(monkeypatch, selectbox_return="aprobado como borrador")
    ficha = GroupFicha(
        id_caso="G-1", estado_revision="aprobado como borrador", tipo_respuesta="respuesta",
        borrador="v1", citas=[], afirmaciones=[], motivo_abstencion=None,
        generado_en=datetime(2026, 1, 1),
    )
    monkeypatch.setattr("app.app.fetch_group_ficha", Mock(return_value=ficha))
    monkeypatch.setattr("app.app.persist_ficha_review_state", Mock())

    render_group_draft(_GROUP)

    assert any("ni autoriza su publicación" in str(call) for call in widgets["success"].call_args_list)


def test_render_group_chat_uses_real_evidence_and_verified_citation_ids(monkeypatch):
    widgets = {name: Mock() for name in ("caption", "warning", "markdown")}
    monkeypatch.setattr("app.app.st.expander", MagicMock())
    monkeypatch.setattr("app.app.st.chat_input", Mock(return_value="¿Qué pasó?"))
    monkeypatch.setattr("app.app.st.chat_message", MagicMock())
    monkeypatch.setattr("app.app.st.spinner", MagicMock())
    monkeypatch.setattr("app.app.st.session_state", {})
    for name, mock in widgets.items():
        monkeypatch.setattr(f"app.app.st.{name}", mock)
    ask_mock = Mock(return_value=ChatResponse("Hecho validado.", False, ["N-real"]))
    monkeypatch.setattr("app.app.ask_group_question", ask_mock)

    render_group_chat(_GROUP)

    assert ask_mock.call_args.args == ("G-1", "¿Qué pasó?")
    assert ask_mock.call_args.kwargs["fichas_path"].name == "fichas.jsonl"
    assert "simulada" not in str(widgets["caption"].call_args_list).lower()
    widgets["caption"].assert_any_call("Citas verificadas: N-real")


def test_render_group_chat_unsupported_question_abstains_without_citations(monkeypatch):
    widgets = {name: Mock() for name in ("caption", "warning", "markdown")}
    monkeypatch.setattr("app.app.st.expander", MagicMock())
    monkeypatch.setattr("app.app.st.chat_input", Mock(return_value="¿Quién ganó?"))
    monkeypatch.setattr("app.app.st.chat_message", MagicMock())
    monkeypatch.setattr("app.app.st.spinner", MagicMock())
    monkeypatch.setattr("app.app.st.session_state", {})
    for name, mock in widgets.items():
        monkeypatch.setattr(f"app.app.st.{name}", mock)
    monkeypatch.setattr(
        "app.app.ask_group_question", Mock(return_value=ChatResponse("No hay evidencia.", True, []))
    )

    render_group_chat(_GROUP)

    assert any("abstención" in str(call).lower() for call in widgets["warning"].call_args_list)
    assert not any("Citas" in str(call) for call in widgets["caption"].call_args_list)


def test_render_group_chat_keeps_the_input_below_every_message(monkeypatch):
    """Messages must go into a container created BEFORE the input, otherwise Streamlit
    draws the new question and answer under the input and the history above it."""

    calls = []
    history_box = MagicMock()
    history_box.__enter__ = Mock(side_effect=lambda: calls.append("enter_box"))
    history_box.__exit__ = Mock(return_value=False)

    def fake_container(*args, **kwargs):
        calls.append("container")
        return history_box

    def fake_chat_input(*args, **kwargs):
        calls.append("chat_input")
        return "¿Qué pasó?"

    monkeypatch.setattr("app.app.st.expander", MagicMock())
    monkeypatch.setattr("app.app.st.container", fake_container)
    monkeypatch.setattr("app.app.st.chat_input", fake_chat_input)
    monkeypatch.setattr("app.app.st.chat_message", MagicMock())
    monkeypatch.setattr("app.app.st.spinner", MagicMock())
    monkeypatch.setattr("app.app.st.session_state", {})
    for name in ("caption", "warning", "markdown"):
        monkeypatch.setattr(f"app.app.st.{name}", Mock())
    monkeypatch.setattr(
        "app.app.ask_group_question", Mock(return_value=ChatResponse("Hecho.", False, []))
    )

    render_group_chat(_GROUP)

    assert calls.index("container") < calls.index("chat_input")
    assert "enter_box" in calls


# --------------------------------------------------------------------------- chat: example questions and fixed-height history

def _ficha_with_claims(claims):
    return GroupFicha(
        id_caso="G-1", estado_revision="nuevo", tipo_respuesta="respuesta",
        borrador="x", citas=[], afirmaciones=[c for c, _ in claims],
        motivo_abstencion=None, generado_en=None, claim_citations=claims,
    )


def test_suggest_questions_are_answerable_and_come_from_the_real_claims(monkeypatch):
    from app.data import suggest_questions

    ficha = _ficha_with_claims(
        [
            ("EEUU dona equipos por $500,000 para habilitar albergues", ["N-1"]),
            ("El Canal de Panamá inaugura la temporada de cruceros", ["N-2"]),
            ("Claim sin cita", []),
        ]
    )

    questions = suggest_questions(ficha, limit=3)

    assert 1 <= len(questions) <= 2  # the uncited claim is never used
    monkeypatch.setattr("app.data.fetch_group_ficha", lambda *a, **k: ficha)
    for question in questions:
        answer = data_module_ask(question)
        assert answer.abstencion is False and answer.citas


def data_module_ask(question):
    from app.data import ask_group_question

    return ask_group_question("G-1", question, motor_path="m", signals_path="s")


def test_suggest_questions_returns_nothing_without_ficha_or_cited_claims():
    from app.data import suggest_questions

    assert suggest_questions(None) == []
    assert suggest_questions(_ficha_with_claims([("Sin cita", [])])) == []


def test_render_group_chat_always_uses_a_fixed_height_history_box(monkeypatch):
    seen = []

    def fake_container(*args, **kwargs):
        seen.append(kwargs.get("height"))
        return MagicMock()

    monkeypatch.setattr("app.app.st.expander", MagicMock())
    monkeypatch.setattr("app.app.st.container", fake_container)
    monkeypatch.setattr("app.app.st.chat_input", Mock(return_value=None))
    monkeypatch.setattr("app.app.st.chat_message", MagicMock())
    monkeypatch.setattr("app.app.st.caption", Mock())
    monkeypatch.setattr("app.app.st.markdown", Mock())
    monkeypatch.setattr("app.app.st.button", Mock(return_value=False))
    monkeypatch.setattr("app.app.fetch_group_ficha", Mock(return_value=None))
    monkeypatch.setattr("app.app.st.session_state", {})

    render_group_chat(_GROUP)

    assert seen == [app_module.CHAT_HISTORY_HEIGHT]


def test_render_group_chat_shows_example_questions_only_while_the_history_is_empty(monkeypatch):
    markdown = Mock()
    button = Mock(return_value=False)
    ficha = _ficha_with_claims([("EEUU dona equipos para albergues", ["N-1"])])
    monkeypatch.setattr("app.app.st.expander", MagicMock())
    monkeypatch.setattr("app.app.st.container", lambda *a, **k: MagicMock())
    monkeypatch.setattr("app.app.st.chat_input", Mock(return_value=None))
    monkeypatch.setattr("app.app.st.chat_message", MagicMock())
    monkeypatch.setattr("app.app.st.caption", Mock())
    monkeypatch.setattr("app.app.st.markdown", markdown)
    monkeypatch.setattr("app.app.st.button", button)
    monkeypatch.setattr("app.app.fetch_group_ficha", Mock(return_value=ficha))

    monkeypatch.setattr("app.app.st.session_state", {})
    render_group_chat(_GROUP)
    assert button.call_count >= 1  # one button per example question

    button.reset_mock()
    monkeypatch.setattr(
        "app.app.st.session_state",
        {"chat_G-1": [{"role": "user", "content": "q"}]},
    )
    render_group_chat(_GROUP)
    button.assert_not_called()


def test_render_group_chat_without_ficha_explains_why_there_are_no_examples(monkeypatch):
    caption = Mock()
    monkeypatch.setattr("app.app.st.expander", MagicMock())
    monkeypatch.setattr("app.app.st.container", lambda *a, **k: MagicMock())
    monkeypatch.setattr("app.app.st.chat_input", Mock(return_value=None))
    monkeypatch.setattr("app.app.st.chat_message", MagicMock())
    monkeypatch.setattr("app.app.st.caption", caption)
    monkeypatch.setattr("app.app.st.markdown", Mock())
    monkeypatch.setattr("app.app.st.button", Mock(return_value=False))
    monkeypatch.setattr("app.app.fetch_group_ficha", Mock(return_value=None))
    monkeypatch.setattr("app.app.st.session_state", {})

    render_group_chat(_GROUP)

    assert any("borrador" in str(c).lower() for c in caption.call_args_list)
