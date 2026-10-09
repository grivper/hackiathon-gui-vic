"""Visual layer for the editorial inbox: global CSS and escaped HTML builders.

Pure functions only (no Streamlit import) so they can be tested without a UI.
Every dynamic string goes through ``html.escape``.
"""

from __future__ import annotations

import re
from html import escape as e
from typing import Iterable

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&family=Source+Sans+3:wght@400;600;700&display=swap');
header[data-testid="stHeader"]{display:none}
.stApp{background:#f4f1ea;font-family:'Source Sans 3',sans-serif;color:#15171c}
.block-container{max-width:1280px;padding:0 40px 56px}
/* No gutter: the full-bleed header must reach the window edge. Wheel, touch and keys still scroll. */
html,body,.stApp,section.stMain{overflow-x:hidden}
section.stMain{scrollbar-width:none}
section.stMain::-webkit-scrollbar{display:none}
.serif{font-family:'Newsreader',Georgia,serif}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}

/* header (bandeja and ficha) */
.hero{background:#15171c;color:#f4f1ea;border-bottom:4px solid #a3162f;
  width:100vw;margin:-1rem 0 24px calc(50% - 50vw);
  padding:36px max(40px,calc(50vw - 640px + 40px));display:flex;flex-wrap:wrap;gap:32px;
  justify-content:space-between;align-items:flex-end;box-sizing:border-box}
.hero .eyebrow{font-size:15px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#e5a3ae}
.hero h1{font-family:'Newsreader',serif;font-size:56px;line-height:1.02;margin:8px 0;color:#f4f1ea;letter-spacing:-1px;padding:0;font-weight:600}
.kpi{display:inline-block;margin-left:36px}
.kpi b{display:block;font-family:'Newsreader',serif;font-size:52px;line-height:1;font-weight:600}
.kpi span{font-size:15px;color:#c9c5b9}
.hero.ficha{flex-direction:column;align-items:flex-start;gap:12px;padding:28px max(40px,calc(50vw - 640px + 40px)) 36px}
.hero.ficha .top{width:100%;display:flex;justify-content:flex-end;align-items:center}
.hero.ficha .meta-row{display:flex;flex-wrap:wrap;align-items:center;gap:10px}
.hero.ficha .tema{color:#f0a7b2}
.hero.ficha .rid{font-size:15px;color:#c9c5b9}
.hero.ficha h1{font-size:44px;line-height:1.1;letter-spacing:-.5px;max-width:980px;margin:0;text-wrap:balance}

.title-row{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:8px;margin:4px 0 2px}
.title-row h2{font-family:'Newsreader',serif;font-size:28px;font-weight:600;margin:0;padding:0}

/* filter bar */
div[class*="st-key-filtros"]{background:#fbfaf6;border:1px solid #ddd8cb;border-radius:14px;padding:16px 18px}

/* bandeja row card */
div[class*="st-key-row-"]{background:#fff;border:1px solid #ddd8cb;border-radius:16px;padding:22px 24px;
  margin-top:14px;transition:box-shadow .15s,transform .15s}
div[class*="st-key-row-"]:hover{box-shadow:0 8px 24px rgba(21,23,28,.10);transform:translateY(-1px)}
.row-main{display:flex;gap:24px;align-items:center}
.row-main .rank{flex:none}

/* bandeja row */
.rank{font-family:'Newsreader',serif;font-size:44px;font-weight:600;color:#a3162f;min-width:64px;line-height:1;white-space:nowrap;font-variant-numeric:tabular-nums}
.tema{font-size:14px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#a3162f}
.meta{font-size:15px;color:#5a5648}
.row-main h3{font-family:'Newsreader',serif;font-size:24px;line-height:1.25;font-weight:600;margin:6px 0 10px;padding:0;text-wrap:balance}
.chip{display:inline-flex;align-items:center;min-height:32px;padding:0 14px;border-radius:999px;background:#ebe7da;
  color:#3b392f;font-size:15px;font-weight:600;margin:0 8px 6px 0}
.chip.warn{background:#fbe9bf;color:#5e4300}
.chip.danger{background:#f9e3e6;color:#6e1124}
.score{width:190px;font-size:15px;font-weight:600;color:#4a473c}
.score b{font-family:'Newsreader',serif;font-size:48px;font-weight:600;display:block;line-height:1;color:#15171c}
.bar{height:6px;border-radius:99px;background:#e6e1d3;overflow:hidden;margin-top:8px}
.bar i{display:block;height:100%;background:#a3162f}

/* ficha */
.alert{display:flex;gap:14px;align-items:flex-start;margin-bottom:6px;background:#fbe9bf;color:#4f3800;border-radius:14px;padding:18px 20px}
.alert b{font-size:17px;display:block}
.alert span{font-size:17px}
.sec,div[class*="st-key-sec-"]{background:#fff;border:1px solid #ddd8cb;border-radius:16px;padding:24px}
.sec{margin:0}
.alert,.sec{margin-bottom:6px}
div[data-testid="stColumn"]>div[data-testid="stVerticalBlock"]{gap:1.1rem}
.sec h2,.sec-h{font-family:'Newsreader',Georgia,serif;font-size:24px;font-weight:600;margin:0 0 12px;padding:0;color:#15171c}
.body{font-size:17px;line-height:1.65;color:#3b392f}
.muted{font-size:17px;color:#5a5648}
.note{font-size:16px;line-height:1.5;color:#5a5648;margin:0 0 12px}
.info{display:flex;gap:12px;align-items:flex-start;background:#e1e9f4;color:#17335a;
  border-radius:12px;padding:14px 16px;font-size:17px;line-height:1.5;margin:12px 0}
.info a{color:#17335a;font-weight:600}

div[class*="st-key-evid-"]{background:#fbfaf6;border:1px solid #ddd8cb;border-radius:14px;padding:20px}
.id{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:15px;color:#5a5648;margin:0 0 14px}
.evid-h{font-family:'Newsreader',Georgia,serif;font-size:21px;line-height:1.3;font-weight:600;margin:0 0 10px;padding:0;text-wrap:balance}
.evid h3{font-family:'Newsreader',Georgia,serif;font-size:21px;line-height:1.3;font-weight:600;margin:0 0 10px;padding:0}
.evid .id{font-family:ui-monospace,Menlo,monospace;font-size:15px;color:#5a5648;margin-bottom:6px}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px 24px;
  border-top:1px solid #e6e1d3;padding-top:14px;margin:4px 0 0}
.kv .k{font-size:14px;font-weight:600;color:#5a5648}
.kv .v{font-size:17px}
.kv .v.na{color:#5a5648}

.aviso{display:flex;gap:12px;align-items:flex-start;background:#fbe9bf;color:#4f3800;
  border-radius:12px;padding:14px 16px;font-size:17px;line-height:1.5;margin-bottom:16px}
.aviso svg{flex:none;margin-top:1px}
.aviso div div{margin-top:4px}
[class*="st-key-vacio_"]{background:#fff;border:1px dashed #b9b29f;border-radius:14px;padding:24px;gap:18px}
[class*="st-key-borrador_"]{background:#fff;border:1px solid #ddd8cb;border-radius:14px;padding:20px}
.vacio-head{display:flex;align-items:center;gap:14px}
.vacio-ico{flex:none;width:48px;height:48px;border-radius:50%;background:#ebe7da;color:#3b392f;
  display:flex;align-items:center;justify-content:center}
.vacio-t{font-size:19px;font-weight:600}
.vacio-s{font-size:16px;color:#5a5648;margin-top:3px}
.vacio-s code,.vacio-nota code{background:#ebe7da;color:#15171c;border-radius:6px;padding:2px 6px;font-size:15px}
.vacio-nota{display:flex;gap:10px;align-items:flex-start;border-top:1px solid #e6e1d3;
  padding-top:16px;font-size:16px;line-height:1.5;color:#5a5648}
.vacio-nota svg{flex:none;margin-top:2px}

/* aside */
.aside{background:#fff;border:1px solid #ddd8cb;border-radius:16px;padding:24px;display:flex;flex-direction:column;gap:18px}
.aside .lbl{font-size:15px;font-weight:600;color:#4a473c}
.aside .big{font-family:'Newsreader',serif;font-size:72px;line-height:1;font-weight:600;margin-top:8px}
.aside .bar{height:8px}
.tiles{display:flex;gap:10px}
.tile{flex:1;border-radius:12px;padding:12px 14px}
.tile .k{font-size:14px;font-weight:600}
.tile{min-width:0}
.tile .v{font-family:'Newsreader',serif;font-size:clamp(17px,1.6vw,22px);font-weight:600}
.tile.danger{background:#f9e3e6;color:#6e1124}
.tile.warn{background:#fbe9bf;color:#5e4300}
.rrow{display:grid;grid-template-columns:40px 1fr 64px;gap:16px;align-items:start;
  padding:16px 0;border-top:1px solid #e6e1d3}
.rbadge{width:40px;height:40px;border-radius:50%;background:#15171c;color:#f4f1ea;
  display:flex;align-items:center;justify-content:center;
  font-family:ui-monospace,Menlo,monospace;font-size:18px;font-weight:700}
.rbadge.low{background:#a3162f;color:#fff}
.rbody{display:flex;flex-wrap:wrap;align-items:center;gap:8px;min-height:40px}
.rchip{display:inline-flex;align-items:center;gap:6px;min-height:30px;padding:0 12px;
  border-radius:999px;background:#ebe7da;font-size:16px}
.rchip span{color:#5a5648}
.rchip b{font-weight:600}
.rlabel{font-size:17px;font-weight:600}
.rnote{flex-basis:100%;font-size:16px;line-height:1.5;color:#5a5648}
.rval{font-family:'Newsreader',Georgia,serif;font-size:30px;line-height:40px;font-weight:600;text-align:right}
.rval.low{color:#a3162f}
.rbar{height:4px;border-radius:99px;background:#e6e1d3;overflow:hidden}
.rbar i{display:block;height:100%;background:#15171c}
.rbar.low i{background:#a3162f}
.rfoot{padding:14px 0 4px;border-top:1px solid #e6e1d3;font-size:16px;color:#5a5648}
.rules{font-size:14px;color:#5a5648}

/* widgets: native text */
.stApp p,.stApp li{font-size:17px;line-height:1.6}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{font-size:15px}
[data-testid="stWidgetLabel"] p{font-size:15px;font-weight:600}
.stSelectbox [data-baseweb="select"] *,.stDateInput input,[data-testid="stChatInput"] textarea{font-size:17px}
.stButton>button p,.stLinkButton>a p{font-size:17px}
div[data-testid="stExpander"] summary p{font-size:18px}
/* Buttons keep light text in EVERY state (link, visited, focus, active); Streamlit otherwise recolours them. */
.stButton>button,.stLinkButton>a,.stLinkButton>a:link,.stLinkButton>a:visited,
.stButton>button:focus,.stButton>button:focus:not(:active),.stLinkButton>a:focus,.stLinkButton>a:focus:not(:active){
  border-radius:999px;background:#15171c;color:#f4f1ea !important;border:0;min-height:44px;font-weight:600;padding:0 20px;text-decoration:none}
.stButton>button:hover,.stButton>button:active,.stLinkButton>a:hover,.stLinkButton>a:active,
.stButton>button:focus-visible,.stLinkButton>a:focus-visible{background:#a3162f;color:#fff !important}
.stButton>button *,.stLinkButton>a *{color:inherit !important}
.st-key-volver-abajo{margin-top:8px}
div[data-baseweb="select"]>div,.stDateInput input{background:#fff;border:1px solid #cfc9b9;border-radius:10px;min-height:44px}
div[data-testid="stExpander"]{border:1px solid #ddd8cb;border-radius:14px;background:#fbfaf6;margin-top:8px}
div[data-testid="stExpander"] summary{font-weight:600;min-height:52px;font-size:18px;color:#15171c}
div[data-testid="stExpander"] summary svg{color:#a3162f}
div[data-testid="stChatInput"]{background:#fff;border:1px solid #cfc9b9;border-radius:14px}
div[data-testid="stChatInput"] textarea{color:#15171c;font-size:17px}
div[data-testid="stChatInput"] button{background:#15171c;color:#f4f1ea;border-radius:10px}
div[data-testid="stChatMessage"]{background:#fbfaf6;border:1px solid #ddd8cb;border-radius:14px;padding:12px 16px}
</style>
"""


_TEMA_LABELS = {
    "economia": "Economía",
    "logistica_canal": "Logística canal",
    "turismo": "Turismo",
    "servicios_publicos": "Servicios públicos",
    "eventos_naturales": "Eventos naturales",
    "regulacion": "Regulación",
    "otros": "Otros",
}


def tema_label(tema: str) -> str:
    """Human label for a topic id; unknown ids fall back to a readable form."""

    return _TEMA_LABELS.get(tema) or tema.replace("_", " ").capitalize()


def _pct(value: float) -> float:
    """Clamp a 0-100 value for use as a bar width."""

    return min(max(float(value), 0.0), 100.0)


def _fmt_pct(value: float) -> str:
    return f"{_pct(value):g}%"


def hero_html(total: int, altas: int, evidencia: int) -> str:
    return (
        '<div class="hero"><div>'
        '<div class="eyebrow">TVN Media / GUI-VIC</div>'
        "<h1>Inteligencia editorial</h1>"
        '<div style="color:#c9c5b9">Priorización local para revisión humana</div>'
        "</div><div>"
        f'<div class="kpi"><b>{int(total)}</b><span>Registros priorizados</span></div>'
        f'<div class="kpi"><b style="color:#f0a7b2">{int(altas)}</b><span>Prioridad alta</span></div>'
        f'<div class="kpi"><b style="color:#f2c777">{int(evidencia)}</b><span>Requieren evidencia</span></div>'
        "</div></div>"
    )


def chips_html(chips: Iterable[tuple[str, str]]) -> str:
    """``chips`` is a list of (text, css modifier)."""

    return "".join(f'<span class="chip {e(kind)}">{e(text)}</span>' for text, kind in chips)


def row_content_html(
    rank: int, tema: str, fecha: str, titulo: str, chips: Iterable[tuple[str, str]]
) -> str:
    """Left side of a bandeja row (rank, topic, date, headline, chips)."""

    return (
        '<div class="row-main">'
        f'<div class="rank">{int(rank):02d}</div>'
        '<div style="min-width:0">'
        f'<span class="tema">{e(tema_label(tema))}</span> <span class="meta">· {e(fecha)}</span>'
        f"<h3>{e(titulo)}</h3>{chips_html(chips)}</div></div>"
    )


def score_block_html(puntaje: float, label: str = "Atención") -> str:
    """Score with its 0-100 bar, used on the bandeja row."""

    return (
        f'<div class="score">{e(label)}<b>{float(puntaje):.1f}</b>'
        f'<div class="bar"><i style="width:{_fmt_pct(puntaje)}"></i></div></div>'
    )


def title_row_html(title: str, note: str) -> str:
    return (
        f'<div class="title-row"><h2 class="serif">{e(title)}</h2>'
        f'<div class="meta">{e(note)}</div></div>'
    )


def ficha_header_html(tema: str, grupo_id: str, titulo: str) -> str:
    return (
        '<div class="hero ficha">'
        '<div class="top"><div class="eyebrow">Inteligencia editorial · TVN Media / GUI-VIC</div></div>'
        f'<div class="meta-row"><span class="tema">{e(tema_label(tema))}</span><span style="color:#8a8573">·</span>'
        f'<span class="rid mono">Registro editorial {e(grupo_id)}</span></div>'
        f"<h1>{e(titulo)}</h1></div>"
    )


_ICON_WARN = (
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 3l10 18H2L12 3z"></path><path d="M12 10v5M12 18v.5"></path></svg>'
)
_ICON_INFO = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="9"></circle><path d="M12 11v5M12 8v.5"></path></svg>'
)
_ICON_FILE = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#5a5648" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5z"></path>'
    '<path d="M14 3v5h5"></path></svg>'
)


def alert_html(title: str, subtitle: str = "") -> str:
    sub = f"<span>{e(subtitle)}</span>" if subtitle else ""
    return f'<div class="alert">{_ICON_WARN}<div><b>{e(title)}</b>{sub}</div></div>'


def heading_html(title: str) -> str:
    return f'<div class="sec-h">{e(title)}</div>'


def section_html(title: str, body: str) -> str:
    paragraphs = "".join(
        f'<div class="body">{e(part)}</div>' for part in body.split("\n\n") if part.strip()
    )
    return f'<div class="sec"><h2>{e(title)}</h2>{paragraphs}</div>'


def muted_section_html(title: str, text: str) -> str:
    return f'<div class="sec"><h2>{e(title)}</h2><div class="muted">{e(text)}</div></div>'


def note_html(text: str) -> str:
    return f'<div class="body">{e(text)}</div>'


_COMPONENT = re.compile(r"([RIUNE])=(\d+(?:\.\d+)?)\s*\(([^()]*)\)")


def _pretty(text: str) -> str:
    """Presentation only: underscores to spaces, True/False to Sí/No."""

    text = text.strip().replace("_", " ")
    return {"True": "Sí", "False": "No"}.get(text, text)


def _criterion_html(detail: str) -> str:
    """Chips (key=value), a plain label, and trailing notes for one component."""

    parts = [p.strip() for p in detail.split(";") if p.strip()]
    main, notes = (parts[0] if parts else ""), parts[1:]
    chips, label = [], []
    for item in (x.strip() for x in main.split(",") if x.strip()):
        if "=" in item:
            key, value = item.split("=", 1)
            chips.append(f'<span class="rchip"><span>{e(_pretty(key))}</span><b>{e(_pretty(value))}</b></span>')
        else:
            label.append(item)
    body = ""
    if label:
        body += f'<span class="rlabel">{e(" ".join(label).replace("_", " "))}</span>'
    body += "".join(chips)
    body += "".join(f'<span class="rnote">{e(n[0].upper() + n[1:])}.</span>' for n in notes)
    return body


def resumen_reporte_html(texto: str, pie: str = "") -> str:
    """"Resumen del reporte": one row per R/I/U/N/E component, parsed from the motor's text.

    Presentation only. When the text does not match the expected format it is shown as is.
    """

    components = _COMPONENT.findall(texto)
    if not components:
        footer = f'<div class="rfoot">{e(pie)}</div>' if pie else ""
        return f'<div class="sec"><h2>Resumen del reporte</h2><div class="body">{e(texto)}</div>{footer}</div>'
    rest = re.sub(r"[;\s]+", " ", _COMPONENT.sub("", texto)).strip()
    footer_text = " ".join(part for part in (rest, pie) if part)
    rows = ""
    for letter, value, detail in components:
        number = float(value)
        low = " low" if number == 0.0 else ""
        rows += (
            '<div class="rrow">'
            f'<div class="rbadge{low}">{letter}</div>'
            f'<div class="rbody">{_criterion_html(detail)}</div>'
            f'<div><div class="rval{low}">{number:.1f}</div>'
            f'<div class="rbar{low}"><i style="width:{_fmt_pct(number * 100)}"></i></div></div>'
            "</div>"
        )
    footer = f'<div class="rfoot">{e(footer_text)}</div>' if footer_text else ""
    return f'<div class="sec"><h2>Resumen del reporte</h2>{rows}{footer}</div>'


def aside_html(
    puntaje: float,
    prioridad: str,
    estado_evidencia: str,
    version_reglas: str,
) -> str:
    return (
        '<div class="aside">'
        f'<div><div class="lbl">Puntaje de atención</div><div class="big">{float(puntaje):.1f}</div>'
        f'<div class="bar"><i style="width:{_fmt_pct(puntaje)}"></i></div></div>'
        '<div class="tiles">'
        f'<div class="tile danger"><div class="k">Prioridad</div><div class="v">{e(prioridad.capitalize())}</div></div>'
        f'<div class="tile warn"><div class="k">Evidencia</div><div class="v">{e(estado_evidencia.capitalize())}</div></div>'
        "</div>"
        f'<div class="rules">Reglas {e(version_reglas)}</div>'
        "</div>"
    )


def info_html(label: str, text: str, href: str | None = None, link_text: str | None = None) -> str:
    """Informational notice. ``label`` is optional bold prefix; ``href`` adds a link."""

    prefix = f"<b>{e(label)}</b> " if label else ""
    body = e(text)
    if href:
        body += f'<a href="{e(href)}">{e(link_text or href)}</a>'
    return f'<div class="info">{_ICON_INFO}<div>{prefix}{body}</div></div>'


_ICON_LOCK = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="5" y="11" width="14" height="10" rx="2"></rect><path d="M8 11V8a4 4 0 018 0v3"></path></svg>'
)


def aviso_html(strong: str, normal: str) -> str:
    """Amber notice for the generated package: first sentence bold, second normal."""

    return f'<div class="aviso">{_ICON_WARN}<div><b>{e(strong)}</b><div>{e(normal)}</div></div></div>'


def empty_head_html() -> str:
    """Head of the "no draft yet" card; the button and note follow inside the same card."""

    return (
        '<div class="vacio-head">'
        f'<div class="vacio-ico">{_ICON_FILE.replace("#5a5648", "currentColor").replace("22", "24")}</div>'
        '<div><div class="vacio-t">Borrador no generado para este grupo</div>'
        '<div class="vacio-s">Ejecutar <code>make generar</code></div></div></div>'
    )


def empty_note_html(text: str) -> str:
    return f'<div class="vacio-nota">{_ICON_LOCK}<div>{e(text)}</div></div>'


def evidence_head_html(titulo: str, id_noticia: str, campo: str | None = None) -> str:
    """Opening of an evidence card; the source button and ``evidence_kv_html`` follow."""

    campo_txt = f" · Campo citado disponible: {e(campo)}" if campo else ""
    return (
        f'<div class="evid-h">{e(titulo)}</div>'
        f'<div class="id">ID de evidencia: {e(id_noticia)}{campo_txt}</div>'
    )


def evidence_kv_html(items: Iterable[tuple[str, str]]) -> str:
    cells = "".join(
        f'<div><div class="k">{e(k)}</div>'
        f'<div class="v{" na" if v == "No disponible" else ""}">{e(v)}</div></div>'
        for k, v in items
    )
    return f'<div class="kv">{cells}</div>'
