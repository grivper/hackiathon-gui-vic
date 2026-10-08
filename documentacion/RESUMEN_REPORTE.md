# Rediseño — "Resumen del reporte" (desglose R / I / U / N / E)

> Para Claude Code en local. **Solo presentación**: no cambies cómo se calcula ni cómo se genera el texto del resumen. Hoy el resumen sale como un párrafo con este formato:
>
> `R=1.0 (tema=servicios_publicos, medio_nacional=True); I=1.0 (alcance=nacional); U=1.0 (antigüedad vs fecha_ref); N=1.0 (repetición=no); E=0.0 (procedencias/fuente primaria; contexto oficial de nivel-tema no suma, ver contexto_oficial)` + una línea final como `Sin repetición detectada en este grupo.`

## Objetivo
Reemplazar ese párrafo por una lista de 5 filas (una por componente), con el mismo contenido. Diseño de referencia: artboard "Resumen del reporte (propuesta)" en https://claude.ai/artifact/HyJwyeDGCu5j5RjZbwbc7D

Cada fila: `[insignia con la letra] [criterio: chips clave/valor o etiqueta] [valor grande a la derecha]`. La E con valor bajo va en carmesí. La línea final (`Sin repetición…`) queda como nota gris al pie.

**No inventes nombres para R, I, N** (Relevancia, Impacto…) a menos que ya existan en el código. Muestra solo lo que dice el texto.

## IMPORTANTE: no duplicar R/I/U/N/E
El panel lateral de la ficha **NO** debe repetir los componentes R/I/U/N/E (ni barras ni valores). Elimina de ese panel el bloque "Componentes R / I / U / N / E" y deja solo: puntaje de atención + barra, tarjetas Prioridad y Evidencia, y "Reglas vX.Y". El desglose completo vive únicamente en "Resumen del reporte". Cada fila lleva además una barra fina bajo el valor (ancho = valor × 100 %, con el valor en 0–1).

## Código (parser + render)

```python
import html, re
import streamlit as st

e = html.escape
COMP = re.compile(r'([RIUNE])=(\d+(?:\.\d+)?)\s*\(([^()]*)\)')

def _pretty(s):
    s = s.strip().replace("_", " ")
    return {"True": "Sí", "False": "No"}.get(s, s)   # solo presentación

def _chips(detalle):
    """detalle: contenido entre paréntesis de un componente."""
    partes = [p.strip() for p in detalle.split(";") if p.strip()]
    principal, notas = (partes[0] if partes else ""), partes[1:]
    chips, etiqueta = [], []
    for item in [x.strip() for x in principal.split(",") if x.strip()]:
        if "=" in item:
            k, v = item.split("=", 1)
            chips.append(f'<span class="rchip"><span>{e(_pretty(k))}</span><b>{e(_pretty(v))}</b></span>')
        else:
            etiqueta.append(item)
    cuerpo = ""
    if etiqueta:
        cuerpo += f'<span class="rlabel">{e(" ".join(etiqueta).replace("_", " "))}</span>'
    cuerpo += "".join(chips)
    nota = "".join(f'<span class="rnote">{e(n[0].upper() + n[1:])}.</span>' for n in notas)
    return cuerpo, nota

def resumen_reporte(texto):
    comps = COMP.findall(texto)
    if not comps:                       # formato inesperado: mostrar el texto tal cual
        st.markdown(f'<div class="sec"><h2>Resumen del reporte</h2>{e(texto)}</div>', unsafe_allow_html=True)
        return
    resto = COMP.sub("", texto)
    resto = re.sub(r'[;\s]+', ' ', resto).strip()          # "Sin repetición detectada…"
    filas = ""
    for letra, valor, detalle in comps:
        bajo = float(valor) == 0.0
        cuerpo, nota = _chips(detalle)
        filas += f"""
        <div class="rrow">
          <div class="rbadge {'low' if bajo else ''}">{letra}</div>
          <div class="rbody">{cuerpo}{nota}</div>
          <div class="rval {'low' if bajo else ''}">{float(valor):.1f}</div>
        </div>"""
    pie = f'<div class="rfoot">{e(resto)}</div>' if resto else ""
    st.markdown(f'<div class="sec"><h2>Resumen del reporte</h2>{filas}{pie}</div>',
                unsafe_allow_html=True)
```

Uso: sustituye donde hoy se pinta el párrafo por `resumen_reporte(texto_del_resumen)`.

## CSS

```css
.rrow{display:grid;grid-template-columns:40px 1fr 64px;gap:16px;align-items:start;
  padding:16px 0;border-top:1px solid #e6e1d3}
.rbadge{width:40px;height:40px;border-radius:50%;background:#15171c;color:#f4f1ea;
  display:flex;align-items:center;justify-content:center;
  font-family:ui-monospace,Menlo,monospace;font-size:16px;font-weight:700}
.rbadge.low{background:#a3162f;color:#fff}
.rbody{display:flex;flex-wrap:wrap;align-items:center;gap:8px;min-height:40px}
.rchip{display:inline-flex;align-items:center;gap:6px;min-height:30px;padding:0 12px;
  border-radius:999px;background:#ebe7da;font-size:14px}
.rchip span{color:#5a5648}
.rchip b{font-weight:600}
.rlabel{font-size:15px;font-weight:600}
.rnote{flex-basis:100%;font-size:14px;line-height:1.5;color:#5a5648}
.rval{font-family:'Newsreader',Georgia,serif;font-size:30px;line-height:40px;font-weight:600;text-align:right}
.rval.low{color:#a3162f}
.rfoot{padding:14px 0 4px;border-top:1px solid #e6e1d3;font-size:14px;color:#5a5648}
```

## Notas
- El parser tolera que el componente E tenga `;` dentro del paréntesis (separa "etiqueta" y "notas").
- Si el texto no coincide con el patrón, se muestra tal cual (no se rompe).
- `True/False → Sí/No` es solo presentación; quítalo si prefieres el valor literal.
- Las claves se muestran con `_` convertido en espacio (`medio_nacional` → `medio nacional`). Las tildes que no estén en el dato original no se añaden.
- Escapa con `html.escape` (ya hecho en el código).
- El panel lateral ya muestra barras R/I/U/N/E: aquí solo el valor en número, para no duplicar.

## Criterios de aceptación
- [ ] El resumen se ve como 5 filas con insignia, criterio y valor.
- [ ] E = 0.0 resaltada en carmesí.
- [ ] Mismo contenido que el párrafo original; nada inventado.
- [ ] Si el formato cambia, cae al texto original sin errores.
