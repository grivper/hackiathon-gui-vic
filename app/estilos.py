"""Visual layer for the editorial inbox: global CSS and escaped HTML builders.

Pure functions only (no Streamlit import) so they can be tested without a UI.
Every dynamic string goes through ``html.escape``.
"""

from __future__ import annotations

from html import escape as e
from typing import Iterable

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&family=Source+Sans+3:wght@400;600;700&display=swap');
header[data-testid="stHeader"]{display:none}
.stApp{background:#f4f1ea;font-family:'Source Sans 3',sans-serif;color:#15171c}
.block-container{max-width:1280px;padding-top:0}
.serif{font-family:'Newsreader',Georgia,serif}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}

/* header (bandeja and ficha) */
.hero{background:#15171c;color:#f4f1ea;border-bottom:4px solid #a3162f;
  padding:36px 40px;margin:0 -4rem 24px;display:flex;flex-wrap:wrap;gap:32px;
  justify-content:space-between;align-items:flex-end}
.hero .eyebrow{font-size:13px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#e5a3ae}
.hero h1{font-family:'Newsreader',serif;font-size:56px;line-height:1.02;margin:8px 0;color:#f4f1ea;letter-spacing:-1px;padding:0;font-weight:600}
.kpi{display:inline-block;margin-left:36px}
.kpi b{display:block;font-family:'Newsreader',serif;font-size:52px;line-height:1;font-weight:600}
.kpi span{font-size:13px;color:#c9c5b9}
.hero.ficha{flex-direction:column;align-items:flex-start;gap:12px;padding:20px 40px 36px}
.hero.ficha .top{width:100%;display:flex;justify-content:flex-end;min-height:44px;align-items:center}
.hero.ficha .meta-row{display:flex;flex-wrap:wrap;align-items:center;gap:10px}
.hero.ficha .tema{color:#f0a7b2}
.hero.ficha .rid{font-size:13px;color:#c9c5b9}
.hero.ficha h1{font-size:44px;line-height:1.1;letter-spacing:-.5px;max-width:980px;margin:0;text-wrap:balance}

.section-title{font-family:'Newsreader',serif;font-size:28px;font-weight:600;margin:24px 0 2px}

/* bandeja row */
.card{display:flex;flex-wrap:wrap;gap:20px 28px;align-items:center;background:#fff;
  border:1px solid #ddd8cb;border-radius:16px;padding:22px 24px;margin-top:14px}
.rank{font-family:'Newsreader',serif;font-size:44px;font-weight:600;color:#a3162f;width:48px;line-height:1}
.tema{font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#a3162f}
.meta{font-size:13px;color:#5a5648}
.card h3{font-family:'Newsreader',serif;font-size:24px;line-height:1.25;font-weight:600;margin:6px 0 10px;padding:0;text-wrap:balance}
.chip{display:inline-flex;align-items:center;min-height:28px;padding:0 12px;border-radius:999px;background:#ebe7da;
  color:#3b392f;font-size:13px;font-weight:600;margin:0 8px 6px 0}
.chip.warn{background:#fbe9bf;color:#5e4300}
.chip.danger{background:#f9e3e6;color:#6e1124}
.score{width:190px;font-size:13px;font-weight:600;color:#4a473c}
.score b{font-family:'Newsreader',serif;font-size:48px;font-weight:600;display:block;line-height:1;color:#15171c}
.bar{height:6px;border-radius:99px;background:#e6e1d3;overflow:hidden;margin-top:8px}
.bar i{display:block;height:100%;background:#a3162f}

/* ficha */
.alert{display:flex;gap:14px;align-items:flex-start;background:#fbe9bf;color:#4f3800;border-radius:14px;padding:18px 20px}
.alert b{font-size:17px;display:block}
.alert span{font-size:15px}
.sec,div[class*="st-key-sec-"]{background:#fff;border:1px solid #ddd8cb;border-radius:16px;padding:24px}
.sec{margin:0}
.alert,.sec{margin-bottom:6px}
div[data-testid="stColumn"]>div[data-testid="stVerticalBlock"]{gap:1.1rem}
.sec h2,.sec-h{font-family:'Newsreader',Georgia,serif;font-size:24px;font-weight:600;margin:0 0 12px;padding:0;color:#15171c}
.body{font-size:15px;line-height:1.65;color:#3b392f}
.muted{font-size:15px;color:#5a5648}
.note{font-size:14px;line-height:1.5;color:#5a5648;margin:0 0 12px}
.info{display:flex;gap:12px;align-items:flex-start;background:#e1e9f4;color:#17335a;
  border-radius:12px;padding:14px 16px;font-size:15px;line-height:1.5;margin:12px 0}
.info a{color:#17335a;font-weight:600}

.evid{border-top:1px solid #e6e1d3;padding-top:18px;margin-top:14px}
.evid h3{font-family:'Newsreader',Georgia,serif;font-size:21px;line-height:1.3;font-weight:600;margin:0 0 10px;padding:0}
.evid .id{font-family:ui-monospace,Menlo,monospace;font-size:13px;color:#5a5648;margin-bottom:6px}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px 24px;
  border-top:1px solid #e6e1d3;padding-top:14px;margin:14px 0 8px}
.kv .k{font-size:12px;font-weight:600;color:#5a5648}
.kv .v{font-size:15px}
.kv .v.na{color:#5a5648}

.empty{display:flex;gap:12px;align-items:center;background:#fff;border:1px dashed #b9b29f;
  border-radius:12px;padding:18px 20px;font-size:15px;color:#3b392f}
.empty code{background:#ebe7da;border-radius:6px;padding:2px 6px;font-size:13px}

/* aside */
.aside{background:#fff;border:1px solid #ddd8cb;border-radius:16px;padding:24px;display:flex;flex-direction:column;gap:18px}
.aside .lbl{font-size:13px;font-weight:600;color:#4a473c}
.aside .big{font-family:'Newsreader',serif;font-size:72px;line-height:1;font-weight:600;margin-top:8px}
.aside .bar{height:8px}
.tiles{display:flex;gap:10px}
.tile{flex:1;border-radius:12px;padding:12px 14px}
.tile .k{font-size:12px;font-weight:600}
.tile .v{font-family:'Newsreader',serif;font-size:26px;font-weight:600}
.tile.danger{background:#f9e3e6;color:#6e1124}
.tile.warn{background:#fbe9bf;color:#5e4300}
.comps{border-top:1px solid #e6e1d3;padding-top:6px}
.comp{display:grid;grid-template-columns:24px 1fr 32px;gap:10px;align-items:center;margin:12px 0;
  font-family:ui-monospace,Menlo,monospace;font-size:13px}
.comp b{font-weight:700}
.comp span{text-align:right}
.comp .bar{margin:0;height:8px}
.comp .bar i{background:#15171c}
.comp.low b,.comp.low span{color:#a3162f}
.comp.low .bar i{background:#a3162f}
.rules{font-size:12px;color:#5a5648}

/* widgets */
.stButton>button,.stLinkButton>a{border-radius:999px;background:#15171c;color:#f4f1ea;border:0;min-height:44px;font-weight:600;padding:0 20px}
.stButton>button:hover,.stLinkButton>a:hover{background:#a3162f;color:#fff}
.stButton>button p,.stLinkButton>a p{color:inherit}
.st-key-volver{position:relative;z-index:5;margin-bottom:-76px}
.st-key-volver button{background:transparent;color:#f4f1ea;padding:0 4px;margin-left:36px}
.st-key-volver button:hover{background:transparent;color:#f0a7b2}
div[data-baseweb="select"]>div,.stDateInput input{background:#fff;border:1px solid #cfc9b9;border-radius:10px;min-height:44px}
div[data-testid="stExpander"]{border:1px solid #ddd8cb;border-radius:14px;background:#fbfaf6;margin-top:8px}
div[data-testid="stExpander"] summary{font-weight:600;min-height:52px;font-size:16px;color:#15171c}
div[data-testid="stExpander"] summary svg{color:#a3162f}
div[data-testid="stChatInput"]{background:#fff;border:1px solid #cfc9b9;border-radius:14px}
div[data-testid="stChatInput"] textarea{color:#15171c;font-size:15px}
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


def section_title_html(title: str, note: str) -> str:
    return f'<div class="section-title">{e(title)}</div><div class="meta">{e(note)}</div>'


def chips_html(chips: Iterable[tuple[str, str]]) -> str:
    """``chips`` is a list of (text, css modifier)."""

    return "".join(f'<span class="chip {e(kind)}">{e(text)}</span>' for text, kind in chips)


def score_card_html(
    rank: int,
    tema: str,
    fecha: str,
    titulo: str,
    chips: Iterable[tuple[str, str]],
    puntaje: float,
) -> str:
    """Ranked bandeja row (the open-ficha button is a native widget beside it)."""

    return (
        '<div class="card">'
        f'<div class="rank">{int(rank)}</div>'
        '<div style="flex:1 1 380px;min-width:0">'
        f'<span class="tema">{e(tema_label(tema))}</span> <span class="meta">· {e(fecha)}</span>'
        f"<h3>{e(titulo)}</h3>{chips_html(chips)}</div>"
        f'<div class="score">Atención<b>{float(puntaje):.1f}</b>'
        f'<div class="bar"><i style="width:{_fmt_pct(puntaje)}"></i></div></div>'
        "</div>"
    )


def ficha_header_html(tema: str, grupo_id: str, titulo: str) -> str:
    return (
        '<div class="hero ficha">'
        '<div class="top"><div class="eyebrow">Inteligencia editorial · TVN Media / GUI-VIC</div></div>'
        f'<div class="meta-row"><span class="tema">{e(tema_label(tema))}</span><span style="color:#8a8573">·</span>'
        f'<span class="rid mono">Registro editorial {e(grupo_id)}</span></div>'
        f"<h1>{e(titulo)}</h1></div>"
    )


def alert_html(title: str, subtitle: str = "") -> str:
    sub = f"<span>{e(subtitle)}</span>" if subtitle else ""
    return f'<div class="alert"><div><b>{e(title)}</b>{sub}</div></div>'


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


def component_bars_html(componentes: dict[str, float]) -> str:
    """R/I/U/N/E bars. The motor stores each component on a 0-1 scale."""

    rows = []
    for letter in "RIUNE":
        value = float(componentes[letter])
        low = letter == "E" and value < 0.4
        klass = f"comp {letter.lower()}{' low' if low else ''}"
        rows.append(
            f'<div class="{klass}"><b>{letter}</b>'
            f'<div class="bar"><i style="width:{_fmt_pct(value * 100)}"></i></div>'
            f"<span>{value:.1f}</span></div>"
        )
    return "".join(rows)


def aside_html(
    puntaje: float,
    prioridad: str,
    estado_evidencia: str,
    componentes: dict[str, float],
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
        '<div class="comps"><div class="lbl" style="padding-top:12px">Componentes R / I / U / N / E</div>'
        f"{component_bars_html(componentes)}"
        f'<div class="rules">Reglas {e(version_reglas)}</div></div>'
        "</div>"
    )


def info_html(label: str, text: str, href: str | None = None, link_text: str | None = None) -> str:
    """Informational notice. ``label`` is optional bold prefix; ``href`` adds a link."""

    prefix = f"<b>{e(label)}</b> " if label else ""
    body = e(text)
    if href:
        body += f'<a href="{e(href)}">{e(link_text or href)}</a>'
    return f'<div class="info"><div>{prefix}{body}</div></div>'


def empty_draft_html() -> str:
    return (
        '<div class="empty">Borrador no generado para este grupo '
        "(ejecutar <code>make generar</code>).</div>"
    )


def evidence_head_html(titulo: str, id_noticia: str, campo: str | None = None) -> str:
    """Opening of an evidence card; the source button and ``evidence_kv_html`` follow."""

    campo_txt = f" · Campo citado disponible: {e(campo)}" if campo else ""
    return (
        '<div class="evid">'
        f"<h3>{e(titulo)}</h3>"
        f'<div class="id">ID de evidencia: {e(id_noticia)}{campo_txt}</div>'
        "</div>"
    )


def evidence_kv_html(items: Iterable[tuple[str, str]]) -> str:
    cells = "".join(
        f'<div><div class="k">{e(k)}</div>'
        f'<div class="v{" na" if v == "No disponible" else ""}">{e(v)}</div></div>'
        for k, v in items
    )
    return f'<div class="kv">{cells}</div>'
