# Rediseño visual — Inteligencia editorial (TVN Media / GUI-VIC)

> Instrucciones para Claude Code en local. Objetivo: aplicar un rediseño **solo visual** a la app existente (Streamlit, según las capturas). **No cambiar lógica, datos, cálculo de puntajes ni reglas (v0.3).** Mantener todos los textos y cifras que la app ya genera.

Diseño de referencia (lienzo): https://claude.ai/artifact/HyJwyeDGCu5j5RjZbwbc7D

## 0. Cómo trabajar

1. Localiza el archivo de la interfaz (probable `app.py` o similar con `st.selectbox`, `st.date_input`, "Registros priorizados", "Abrir ficha"). Léelo entero antes de editar.
2. Identifica los nombres reales de campos del registro (titular, tema, fecha, procedencias, estado de evidencia, n.º de registros, puntaje, id, prioridad, componentes R/I/U/N/E, resumen). Usa esos nombres; los de abajo son ilustrativos.
3. Conserva: filtros (Tema, Desde, Hasta), orden (mayor puntaje → urgencia U → identificador), KPIs, la navegación bandeja ↔ ficha y los textos exactos (ej. "Prioridad Alto: requiere investigación y no es publicable.").
4. Aplica el CSS global (sección 2), reemplaza el dibujado de cabecera/tarjetas/ficha por las funciones HTML (sección 3) y deja los widgets nativos (filtros, botones) en Streamlit.
5. Escapa SIEMPRE el texto dinámico con `html.escape` antes de meterlo en HTML.
6. Al terminar, ejecuta la app y verifica visualmente bandeja y ficha; no rompas tests existentes.

## 1. Dirección de diseño

"Mesa de redacción": cabecera oscura con las cifras clave, tipografía editorial con serif para titulares y números, filas rankeadas con barra de puntaje, ficha en dos columnas con panel lateral de puntaje.

### Tokens

| Token | Valor | Uso |
|---|---|---|
| paper | `#f4f1ea` | fondo de la app |
| paper-2 | `#fbfaf6` | barra de filtros |
| surface | `#ffffff` | tarjetas y paneles |
| ink | `#15171c` | texto, cabecera, botón |
| ink-muted | `#5a5648` | texto secundario (contraste AA sobre paper) |
| ink-soft | `#3b392f` | cuerpo en paneles |
| accent | `#a3162f` | acento carmesí, rank, barras, hover |
| accent-light | `#f0a7b2` / `#e5a3ae` | acento sobre fondo oscuro |
| gold-light | `#f2c777` | KPI "Requieren evidencia" sobre oscuro |
| line | `#ddd8cb` | bordes |
| track | `#e6e1d3` | fondo de barras |
| chip | `#ebe7da` / texto `#3b392f` | chips neutros |
| warn-bg / warn-text | `#fbe9bf` / `#5e4300` | evidencia insuficiente, aviso |
| danger-bg / danger-text | `#f9e3e6` / `#6e1124` | prioridad alta |

Tipografía (Google Fonts): **Newsreader** (500/600; titulares, números grandes) + **Source Sans 3** (400/600/700; resto). Monoespaciada del sistema para ids y componentes.

Escala: título hero 56px · titular ficha 44px · titular tarjeta 24px · KPI hero 52px · puntaje tarjeta 48px · puntaje ficha 72px · cuerpo 15px · meta 13px · eyebrow 12–13px mayúsculas con `letter-spacing` 1–2px.
Radios: tarjetas 16px, paneles 16px, filtros 10px, chips y botones 999px. Altura mínima de controles: 44px.

## 2. CSS global

```python
import html
import streamlit as st

e = html.escape

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600&family=Source+Sans+3:wght@400;600;700&display=swap');
.stApp{background:#f4f1ea;font-family:'Source Sans 3',sans-serif;color:#15171c}
.block-container{max-width:1280px;padding-top:0}
.serif{font-family:'Newsreader',Georgia,serif}

/* cabecera */
.hero{background:#15171c;color:#f4f1ea;border-bottom:4px solid #a3162f;
  padding:36px 40px;margin:0 -4rem 24px;display:flex;flex-wrap:wrap;gap:32px;
  justify-content:space-between;align-items:flex-end}
.hero .eyebrow{font-size:13px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#e5a3ae}
.hero h1{font-family:'Newsreader',serif;font-size:56px;line-height:1.02;margin:8px 0;color:#f4f1ea;letter-spacing:-1px}
.kpi{display:inline-block;margin-left:36px}
.kpi b{display:block;font-family:'Newsreader',serif;font-size:52px;line-height:1;font-weight:600}
.kpi span{font-size:13px;color:#c9c5b9}

/* tarjeta de bandeja */
.card{display:flex;flex-wrap:wrap;gap:20px 28px;align-items:center;background:#fff;
  border:1px solid #ddd8cb;border-radius:16px;padding:22px 24px;margin-top:14px}
.rank{font-family:'Newsreader',serif;font-size:44px;font-weight:600;color:#a3162f;width:48px;line-height:1}
.tema{font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#a3162f}
.meta{font-size:13px;color:#5a5648}
.card h3{font-family:'Newsreader',serif;font-size:24px;line-height:1.25;font-weight:600;margin:6px 0 10px}
.chip{display:inline-block;padding:4px 12px;border-radius:999px;background:#ebe7da;
  color:#3b392f;font-size:13px;font-weight:600;margin:0 8px 6px 0}
.chip.warn{background:#fbe9bf;color:#5e4300}
.chip.danger{background:#f9e3e6;color:#6e1124}
.score{width:190px;font-size:13px;font-weight:600;color:#4a473c}
.score b{font-family:'Newsreader',serif;font-size:48px;font-weight:600;display:block;line-height:1;color:#15171c}
.bar{height:6px;border-radius:99px;background:#e6e1d3;overflow:hidden;margin-top:8px}
.bar i{display:block;height:100%;background:#a3162f}

/* ficha */
.alert{background:#fbe9bf;color:#4f3800;border-radius:14px;padding:18px 20px;margin-bottom:16px}
.alert b{font-size:17px}
.panel{background:#fff;border:1px solid #ddd8cb;border-radius:16px;padding:24px;margin-bottom:16px}
.panel h3{font-family:'Newsreader',serif;font-size:24px;font-weight:600;margin:0 0 10px}
.comp{display:grid;grid-template-columns:24px 1fr 32px;gap:10px;align-items:center;margin:10px 0;
  font-family:ui-monospace,Menlo,monospace;font-size:13px}
.comp .bar{margin:0;height:8px}
.comp .bar i.dark{background:#15171c}

/* widgets nativos */
.stButton>button{border-radius:999px;background:#15171c;color:#f4f1ea;border:0;min-height:44px;font-weight:600;padding:0 20px}
.stButton>button:hover{background:#a3162f;color:#fff}
div[data-baseweb="select"]>div, .stDateInput input{background:#fff;border:1px solid #cfc9b9;border-radius:10px;min-height:44px}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
```

Si la cabecera se desborda lateralmente, ajusta `margin:0 -4rem 24px` (según versión de Streamlit puede ser `-1rem` o `-5rem`). Si `padding-top:0` deja la barra superior de Streamlit encima, oculta `header[data-testid="stHeader"]{display:none}`.

## 3. Componentes

### 3.1 Cabecera con KPIs
Textos: eyebrow "TVN Media / GUI-VIC", título "Inteligencia editorial", subtítulo "Priorización local para revisión humana". KPIs: "Registros priorizados" (blanco), "Prioridad alta" (`#f0a7b2`), "Requieren evidencia" (`#f2c777`).

```python
def cabecera(total, altas, evidencia):
    st.markdown(f"""
    <div class="hero"><div>
      <div class="eyebrow">TVN Media / GUI-VIC</div>
      <h1>Inteligencia editorial</h1>
      <div style="color:#c9c5b9">Priorización local para revisión humana</div>
    </div><div>
      <div class="kpi"><b>{total}</b><span>Registros priorizados</span></div>
      <div class="kpi"><b style="color:#f0a7b2">{altas}</b><span>Prioridad alta</span></div>
      <div class="kpi"><b style="color:#f2c777">{evidencia}</b><span>Requieren evidencia</span></div>
    </div></div>""", unsafe_allow_html=True)
```

### 3.2 Filtros
Mantén los widgets nativos (Tema, Desde, Hasta) en una fila (`st.columns([2,1,1])`), justo debajo de la cabecera. Debajo, un `st.markdown` con encabezado "Bandeja de revisión" (serif 28px) y la nota "Orden: mayor puntaje, luego urgencia (U) y finalmente identificador." en `.meta`.

### 3.3 Tarjeta de bandeja
Fila numerada (1, 2, …) según el orden ya calculado. Texto de evidencia: "Evidencia insuficiente · N registros"; chip `warn` cuando el estado es Insuficiente (usa neutro para otros estados). La barra de puntaje asume escala 0–100: si tu puntaje usa otra escala, cambia el `width`.

```python
def tarjeta(i, r):
    cls = "warn" if r["evidencia"].lower() == "insuficiente" else ""
    st.markdown(f"""
    <div class="card">
      <div class="rank">{i}</div>
      <div style="flex:1 1 380px;min-width:0">
        <span class="tema">{e(r['tema'])}</span> <span class="meta">· {e(r['fecha'])}</span>
        <h3>{e(r['titulo'])}</h3>
        <span class="chip {cls}">Evidencia {e(r['evidencia'].lower())} · {r['n_registros']} registros</span>
        <span class="chip">{r['procedencias']} procedencias distintas</span>
      </div>
      <div class="score">Atención<b>{r['puntaje']:.1f}</b>
        <div class="bar"><i style="width:{min(max(r['puntaje'],0),100)}%"></i></div></div>
    </div>""", unsafe_allow_html=True)
    if st.button("Abrir ficha →", key=f"abrir_{r['id']}"):
        st.session_state.ficha = r["id"]
        st.rerun()
```

Nota: un `st.button` no puede ir dentro del HTML; queda debajo de la tarjeta. Opcional: ponerlo a la derecha con `st.columns([6,1])` (tarjeta en la 1.ª, botón en la 2.ª).

### 3.4 Ficha
Layout: botón "← Volver a la bandeja" → eyebrow con tema y "Registro {id}" → titular (serif 44px) → dos columnas `[2,1]`.

- **Izquierda:** aviso amarillo "Prioridad {prioridad}: requiere investigación" + "No es publicable."; panel "Resumen del reporte" con el texto actual; panel "Evidencia y procedencias" con chips ("N artículos agrupados", "N procedencias distintas (no repeticiones)") y el texto "Basado únicamente en titular/metadatos. La confirmación editorial sigue pendiente."
- **Derecha (panel lateral):** "Puntaje de atención" con número 72px + barra; dos mini-tarjetas "Prioridad" (fondo `#f9e3e6`, texto `#6e1124`) y "Evidencia" (fondo `#fbe9bf`, texto `#5e4300`); lista de componentes R/I/U/N/E con barras (valor 0–1 → ancho `valor*100%`; **E en acento carmesí** cuando es bajo/0, el resto en `ink`) y pie "Reglas v0.3" (usa la versión real de reglas, no la fijes).

```python
def ficha(r):
    if st.button("← Volver a la bandeja"):
        st.session_state.ficha = None
        st.rerun()
    st.markdown(
        f"<span class='tema'>{e(r['tema'])}</span> <span class='meta'>· Registro {e(r['id'])}</span>"
        f"<h1 class='serif' style='font-size:44px;line-height:1.1'>{e(r['titulo'])}</h1>",
        unsafe_allow_html=True)
    izq, der = st.columns([2, 1])
    with izq:
        st.markdown(
            f"<div class='alert'><b>Prioridad {e(r['prioridad'])}: requiere investigación</b><br>No es publicable.</div>",
            unsafe_allow_html=True)
        st.markdown(
            f"<div class='panel'><h3>Resumen del reporte</h3>{e(r['resumen'])}</div>",
            unsafe_allow_html=True)
        st.markdown(
            f"<div class='panel'><h3>Evidencia y procedencias</h3>"
            f"<span class='chip'>{r['n_articulos']} artículos agrupados</span>"
            f"<span class='chip'>{r['procedencias']} procedencias distintas (no repeticiones)</span>"
            f"<p>Basado únicamente en titular/metadatos. La confirmación editorial sigue pendiente.</p></div>",
            unsafe_allow_html=True)
    with der:
        comps = "".join(
            f"<div class='comp'><b>{k}</b><div class='bar'><i class='{'' if k=='E' else 'dark'}' "
            f"style='width:{r[k]*100}%'></i></div><span>{r[k]:.1f}</span></div>"
            for k in "RIUNE")
        st.markdown(
            f"<div class='panel'><div class='meta'>Puntaje de atención</div>"
            f"<div class='serif' style='font-size:72px;line-height:1;font-weight:600'>{r['puntaje']:.1f}</div>"
            f"<div class='bar' style='height:8px'><i style='width:{min(max(r['puntaje'],0),100)}%'></i></div>"
            f"<p><span class='chip danger'>Prioridad {e(r['prioridad'])}</span>"
            f"<span class='chip warn'>Evidencia {e(r['evidencia'].lower())}</span></p>"
            f"<div class='meta'>Componentes R / I / U / N / E</div>{comps}"
            f"<div class='meta'>Reglas {e(r['reglas'])}</div></div>",
            unsafe_allow_html=True)
```

### 3.5 Enrutado
```python
if st.session_state.get("ficha"):
    ficha(registros[st.session_state.ficha])
else:
    cabecera(len(lista), altas, requieren_evidencia)
    # filtros existentes
    for i, r in enumerate(lista, 1):
        tarjeta(i, r)
```
Integra esto con la navegación que la app ya tenga (si usa `query_params` u otro mecanismo, respétalo en vez de `session_state`).

## 4. Reglas de calidad
- Contraste mínimo AA: no usar grises más claros que `#5a5648` sobre `#f4f1ea`.
- Objetivos táctiles ≥ 44px.
- Sin emojis ni iconos decorativos; solo texto y SVG simple si hace falta.
- Responsive: las tarjetas usan `flex-wrap`; la ficha se apila en móvil (`st.columns` ya lo hace).
- No inventar datos: si un campo no existe en el registro, omite ese elemento.

## 5. Criterios de aceptación
- [ ] Bandeja: cabecera oscura con 3 KPIs, filtros, filas numeradas con chips, puntaje y barra.
- [ ] Ficha: titular grande, aviso amarillo, resumen, evidencia, panel lateral con R/I/U/N/E.
- [ ] Navegación bandeja ↔ ficha intacta.
- [ ] Mismos textos y valores que antes; ninguna lógica modificada.
- [ ] Texto dinámico escapado.
