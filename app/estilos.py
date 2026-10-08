"""Visual layer for the editorial inbox: global CSS and escaped HTML builders.

Pure functions only (no Streamlit import) so they can be tested without a UI.
Every dynamic string goes through ``html.escape``.
"""

from __future__ import annotations

from html import escape as e
from typing import Iterable

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600&family=Source+Sans+3:wght@400;600;700&display=swap');
header[data-testid="stHeader"]{display:none}
.stApp{background:#f4f1ea;font-family:'Source Sans 3',sans-serif;color:#15171c}
.block-container{max-width:1280px;padding-top:0}
.serif{font-family:'Newsreader',Georgia,serif}

.hero{background:#15171c;color:#f4f1ea;border-bottom:4px solid #a3162f;
  padding:36px 40px;margin:0 -4rem 24px;display:flex;flex-wrap:wrap;gap:32px;
  justify-content:space-between;align-items:flex-end}
.hero .eyebrow{font-size:13px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#e5a3ae}
.hero h1{font-family:'Newsreader',serif;font-size:56px;line-height:1.02;margin:8px 0;color:#f4f1ea;letter-spacing:-1px;padding:0}
.kpi{display:inline-block;margin-left:36px}
.kpi b{display:block;font-family:'Newsreader',serif;font-size:52px;line-height:1;font-weight:600}
.kpi span{font-size:13px;color:#c9c5b9}

.section-title{font-family:'Newsreader',serif;font-size:28px;font-weight:600;margin:24px 0 2px}

.card{display:flex;flex-wrap:wrap;gap:20px 28px;align-items:center;background:#fff;
  border:1px solid #ddd8cb;border-radius:16px;padding:22px 24px;margin-top:14px}
.rank{font-family:'Newsreader',serif;font-size:44px;font-weight:600;color:#a3162f;width:48px;line-height:1}
.tema{font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#a3162f}
.meta{font-size:13px;color:#5a5648}
.card h3{font-family:'Newsreader',serif;font-size:24px;line-height:1.25;font-weight:600;margin:6px 0 10px;padding:0}
.chip{display:inline-block;padding:4px 12px;border-radius:999px;background:#ebe7da;
  color:#3b392f;font-size:13px;font-weight:600;margin:0 8px 6px 0}
.chip.warn{background:#fbe9bf;color:#5e4300}
.chip.danger{background:#f9e3e6;color:#6e1124}
.score{width:190px;font-size:13px;font-weight:600;color:#4a473c}
.score b{font-family:'Newsreader',serif;font-size:48px;font-weight:600;display:block;line-height:1;color:#15171c}
.bar{height:6px;border-radius:99px;background:#e6e1d3;overflow:hidden;margin-top:8px}
.bar i{display:block;height:100%;background:#a3162f}

.panel{background:#fff;border:1px solid #ddd8cb;border-radius:16px;padding:16px 24px;margin:10px 0}
.comp{display:grid;grid-template-columns:24px 1fr 44px;gap:10px;align-items:center;margin:8px 0;
  font-family:ui-monospace,Menlo,monospace;font-size:13px}
.comp .bar{margin:0;height:8px}
.comp .bar i.dark{background:#15171c}

.stButton>button{border-radius:999px;background:#15171c;color:#f4f1ea;border:0;min-height:44px;font-weight:600;padding:0 20px}
.stButton>button:hover{background:#a3162f;color:#fff}
div[data-baseweb="select"]>div, .stDateInput input{background:#fff;border:1px solid #cfc9b9;border-radius:10px;min-height:44px}
</style>
"""


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


def score_card_html(
    rank: int,
    tema: str,
    fecha: str,
    titulo: str,
    chips: Iterable[tuple[str, str]],
    puntaje: float,
) -> str:
    """Ranked card header. ``chips`` is a list of (text, css modifier)."""

    chips_html = "".join(
        f'<span class="chip {e(kind)}">{e(text)}</span>' for text, kind in chips
    )
    return (
        '<div class="card">'
        f'<div class="rank">{int(rank)}</div>'
        '<div style="flex:1 1 380px;min-width:0">'
        f'<span class="tema">{e(tema)}</span> <span class="meta">· {e(fecha)}</span>'
        f"<h3>{e(titulo)}</h3>{chips_html}</div>"
        f'<div class="score">Puntaje<b>{float(puntaje):.1f}</b>'
        f'<div class="bar"><i style="width:{_fmt_pct(puntaje)}"></i></div></div>'
        "</div>"
    )


def component_bars_html(componentes: dict[str, float]) -> str:
    """R/I/U/N/E bars on a 0-100 scale; a low E is highlighted in crimson."""

    rows = []
    for letter in "RIUNE":
        value = componentes[letter]
        low_e = letter == "E" and value < 40
        klass = "" if low_e else "dark"
        rows.append(
            f'<div class="comp"><b>{letter}</b>'
            f'<div class="bar"><i class="{klass}" style="width:{_fmt_pct(value)}"></i></div>'
            f"<span>{float(value):.1f}</span></div>"
        )
    return '<div class="panel"><div class="meta">Componentes R / I / U / N / E</div>' + "".join(rows) + "</div>"
