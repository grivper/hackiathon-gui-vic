# Anexo v2 — Interior del expander (Evidencia, Contexto oficial, Consulta, Paquete)

> Para Claude Code en local. **Reemplaza** el anexo anterior (pestañas) y **corrige** las secciones 3.4/3.5 de `REDISENO_UI.md`. La app NO tiene una vista "ficha" aparte: todo vive en **expanders dentro de cada tarjeta**. **Mantén esa estructura. No uses `st.tabs`, no crees navegación nueva y no cambies lógica, datos ni textos.** Solo estilo.

Diseño de referencia (artboard "Ficha"): https://claude.ai/artifact/HyJwyeDGCu5j5RjZbwbc7D

## ESTRUCTURA (lo que muestra el lienzo; reprodúcela tal cual)

Además de este anexo van dos archivos de referencia con el HTML exacto del diseño (`Bandeja_referencia.html` y `Ficha_referencia.html`). **Léelos**: contienen los tamaños, espacios, colores y el orden de cada bloque. No se ejecutan solos (son maquetas); úsalos para copiar estructura y valores, no como código de la app.

### Bandeja (pantalla principal)

```
┌─ HERO (fondo #15171c, borde inferior carmesí 4px) ───────────────────────┐
│ izq: eyebrow "TVN Media / GUI-VIC" · H1 "Inteligencia editorial" · subtítulo │
│ der: 3 KPIs en fila (Registros priorizados | Prioridad alta | Requieren evidencia) │
└──────────────────────────────────────────────────────────────────────────┘
┌─ BARRA DE FILTROS (crema #fbfaf6, borde, radio 14) ──────────────────────┐
│ Tema (ancho 2) │ Desde │ Hasta                                           │
└──────────────────────────────────────────────────────────────────────────┘
"Bandeja de revisión" (serif 28)  ........  nota: Orden: mayor puntaje, luego urgencia (U)…
┌─ TARJETA × N (blanca, borde, radio 16) ──────────────────────────────────┐
│ [N.º rank carmesí] [TEMA · fecha / titular serif 24 / chips evidencia + procedencias] │
│ [Atención + 90.0 + barra]                              [Abrir ficha →]   │
└──────────────────────────────────────────────────────────────────────────┘
   └─ debajo de cada tarjeta: el st.expander existente → interior (abajo)
```

### Interior de la ficha (dentro del expander)

Es **una columna ancha a la izquierda (≈2/3) y un panel lateral a la derecha (≈1/3)**. En pantallas estrechas el panel lateral baja debajo (`st.columns` ya apila).

```
┌─ AVISO ÁMBAR (ancho completo): "Prioridad Alto: requiere investigación" / "No es publicable." ┐
├───────────────────────────────────────────────┬──────────────────────────────┤
│ COLUMNA IZQUIERDA (2/3)                       │ PANEL LATERAL (1/3)          │
│ 1. Resumen del reporte                        │ Puntaje de atención 90.0 + barra │
│ 2. Evidencia y procedencias                   │ [Prioridad: Alto] [Evidencia: Insuficiente] │
│    · chips (artículos / procedencias)         │ Componentes R / I / U / N / E │
│    · texto "Basado únicamente en titular…"    │   (barras; E en carmesí)     │
│    · aviso azul "Por verificar: …"            │ "Reglas v0.3"                │
│    · tarjeta de cita:                         │                              │
│        titular · ID de evidencia · botón      │                              │
│        "Abrir fuente original" · cuadrícula   │                              │
│        2×2 (Medio/origen, Procedencia,        │                              │
│        Fecha publicación, Fecha detección)    │                              │
│ 3. Contexto oficial                           │                              │
│ 4. Consulta                                   │                              │
│    ▸ Consulta sobre evidencia validada        │                              │
│    ▸ Paquete generado y revisión humana       │                              │
└───────────────────────────────────────────────┴──────────────────────────────┘
```

### Equivalencias lienzo → app (para no duplicar)
| En el lienzo | En la app |
|---|---|
| Cabecera oscura de la ficha con "← Volver a la bandeja", tema, id y titular | **No se crea.** La tarjeta de la bandeja ya cumple ese papel; el id puede mostrarse en la tarjeta o al inicio del expander |
| Enlace "Abrir ficha" (navega a otra pantalla) | Es el botón/encabezado que **abre el expander** de esa tarjeta |
| Dos artboards separados (Bandeja y Ficha) | Una sola pantalla: la ficha vive dentro del expander de cada tarjeta |
| Sub-secciones "Consulta" y "Paquete" como `<details>` abiertos | Los `st.expander` internos que ya existen (conserva su estado inicial) |

## Qué se ve dentro del expander (en este orden)

1. Aviso de prioridad (ámbar) + resumen del reporte + panel de puntaje con R/I/U/N/E → ver `REDISENO_UI.md` (clases `.alert`, `.panel`, `.comp`, `.bar`).
2. **Evidencia y procedencias** (esta guía, §1).
3. **Contexto oficial** (§2).
4. **Consulta** con dos sub-expanders (§3): "Consulta sobre evidencia validada" y "Paquete generado y revisión humana".

Dentro del expander usa `st.columns([2, 1])`: izquierda (aviso, resumen, evidencia, contexto, consulta) y derecha (panel de puntaje). Si el ancho es poco, apila.

## CSS adicional

```css
/* expander de la tarjeta y sub-expanders */
div[data-testid="stExpander"]{border:1px solid #ddd8cb;border-radius:14px;background:#fbfaf6;margin-top:8px}
div[data-testid="stExpander"] summary{font-weight:600;min-height:52px;font-size:16px}
div[data-testid="stExpander"] summary svg{color:#a3162f}

/* secciones dentro del expander */
.sec{background:#fff;border:1px solid #ddd8cb;border-radius:16px;padding:24px;margin-bottom:16px}
.sec h2{font-family:'Newsreader',Georgia,serif;font-size:24px;font-weight:600;margin:0 0 12px}
.note{font-size:14px;line-height:1.5;color:#5a5648;margin:0 0 12px}

/* aviso informativo "Por verificar" (reemplaza el azul por defecto de st.info) */
.info{display:flex;gap:12px;align-items:flex-start;background:#e1e9f4;color:#17335a;
  border-radius:12px;padding:14px 16px;font-size:15px;line-height:1.5;margin:12px 0}

/* tarjeta de evidencia */
.evid{background:#fbfaf6;border:1px solid #ddd8cb;border-radius:14px;padding:20px}
.evid h3{font-family:'Newsreader',Georgia,serif;font-size:21px;line-height:1.3;font-weight:600;margin:0 0 10px}
.evid .id{font-family:ui-monospace,Menlo,monospace;font-size:13px;color:#5a5648;margin-bottom:14px}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px 24px;
  border-top:1px solid #e6e1d3;padding-top:14px;margin-top:14px}
.kv .k{font-size:12px;font-weight:600;color:#5a5648}
.kv .v{font-size:15px}
.kv .v.na{color:#5a5648}

/* estado vacío del borrador */
.empty{display:flex;gap:12px;align-items:center;background:#fff;border:1px dashed #b9b29f;
  border-radius:12px;padding:18px 20px;font-size:15px;color:#3b392f}
.empty code{background:#ebe7da;border-radius:6px;padding:2px 6px;font-size:13px}

/* chat: campo de consulta (st.chat_input / st.text_input) */
div[data-testid="stChatInput"]{background:#fff;border:1px solid #cfc9b9;border-radius:14px}
div[data-testid="stChatInput"] textarea{color:#15171c;font-size:15px}
div[data-testid="stChatInput"] button{background:#15171c;color:#f4f1ea;border-radius:10px}
div[data-testid="stChatMessage"]{background:#fbfaf6;border:1px solid #ddd8cb;border-radius:14px;padding:12px 16px}

/* el botón "Abrir fuente original" ya hereda .stButton>button (negro, píldora, hover carmesí) */
```

Importante (se vio en las capturas): el campo de chat y los encabezados de los sub-expanders salen **oscuros con texto casi invisible** (texto oscuro sobre fondo oscuro). Con el CSS de arriba deben quedar claros con texto `#15171c`. Si el tema oscuro de Streamlit sigue aplicando, fuerza el tema claro en `.streamlit/config.toml`:

```toml
[theme]
base = "light"
backgroundColor = "#f4f1ea"
secondaryBackgroundColor = "#fbfaf6"
textColor = "#15171c"
primaryColor = "#a3162f"
font = "sans serif"
```

## §1 Evidencia y procedencias

Mantén los datos y textos actuales. Estructura visual:

```python
def evidencia_html(r, ev):
    # r = registro; ev = evidencia citada. Usa los nombres de campo reales.
    return f"""
    <div class="sec">
      <h2>Evidencia y procedencias</h2>
      <span class="chip">{r['n_articulos']} artículos agrupados</span>
      <span class="chip">{r['procedencias']} procedencias distintas (no repeticiones)</span>
      <p>{e(r['texto_base'])}</p>   <!-- "Basado únicamente en titular/metadatos. La confirmación editorial sigue pendiente." -->
      <div class="info">{e(r['aviso_verificar'])}</div> <!-- "Por verificar: confirme el hecho con procedencias distintas; requiere investigación y no es publicable." -->
      <div class="evid">
        <h3>{e(ev['titulo'])}</h3>
        <div class="id">ID de evidencia: {e(ev['id'])} · Campo citado disponible: {e(ev['campo'])}</div>
        <!-- aquí va el st.button / st.link_button "Abrir fuente original" (no puede ir dentro del HTML) -->
        <div class="kv">
          <div><div class="k">Medio/origen</div><div class="v">{e(ev['medio'])}</div></div>
          <div><div class="k">Procedencia</div><div class="v">{e(ev['procedencia'])}</div></div>
          <div><div class="k">Fecha de publicación/original</div><div class="v">{e(ev['fecha_pub'])}</div></div>
          <div><div class="k">Fecha de detección</div><div class="v na">{e(ev['fecha_det'])}</div></div>
        </div>
      </div>
    </div>"""
```

Como Streamlit no permite widgets dentro de HTML, parte la tarjeta en tres `st.markdown` consecutivos: (a) HTML hasta el `.id`, (b) el botón nativo "Abrir fuente original", (c) el bloque `.kv`. Para que se vean como una sola tarjeta usa `st.container(border=True)` con el borde/fondo de `.evid`, o simplifica: botón después del bloque `.kv`. Si ya usas `st.link_button`, consérvalo.

Para el aviso, si hoy usas `st.info(...)`, cámbialo por `st.markdown(f'<div class="info">{e(texto)}</div>', unsafe_allow_html=True)`. Los chips: `.chip` de `REDISENO_UI.md`.

## §2 Contexto oficial

Panel `.sec` con título "Contexto oficial" y el contenido que la app ya muestre. Si no hay contenido, en el diseño se muestra "Sin contexto oficial disponible para este registro." en `.note`. **Antes de añadir ese texto, comprueba qué dice la app cuando está vacío y conserva ese texto**; si no muestra nada, no inventes y deja solo el título o el texto del diseño, a elección.

## §3 Consulta y Paquete

Título "Consulta" en `.sec` (`<h2>`) y, debajo, los dos `st.expander` que ya existen (mantén sus nombres, su estado y su lógica):

- **"Consulta sobre evidencia validada"**: nota `.note` "La respuesta es extractiva: solo recupera afirmaciones y citas validadas de la ficha." y el campo "Escribe tu consulta aquí…" (el actual). Solo estilo.
- **"Paquete generado y revisión humana"**: nota `.note` "Información generada: el borrador no equivale a información verificada ni autoriza publicación." y, si no hay borrador, el estado vacío:

```python
st.markdown(
    '<div class="empty">Borrador no generado para este grupo '
    '(ejecutar <code>make generar</code>).</div>',
    unsafe_allow_html=True)
```
  Si hay borrador, muéstralo como hoy, pero dentro de un contenedor con la misma tarjeta (`.sec` sin título) y sin quitar la nota de arriba.

Reemplaza `st.info(...)` del "Borrador no generado…" por el `.empty` (ya no azul).

## Reglas
- No cambiar lógica, llamadas, claves de estado ni textos. Todo widget dentro del bucle lleva el id del registro en su `key`.
- Escapar con `html.escape` todo texto dinámico.
- No agregar `st.tabs` ni vista de ficha. Eso quedó descartado para hoy.
- Contraste mínimo AA y objetivos táctiles ≥ 44px.
- Si un selector CSS de Streamlit no aplica en tu versión, inspecciona el DOM y ajusta; evita `!important` salvo necesidad.

## Criterios de aceptación
- [ ] Expander de cada tarjeta: aviso ámbar, resumen, evidencia con tarjeta de cita, contexto oficial, consulta y paquete.
- [ ] El chat y los encabezados de sub-expanders se leen (sin texto oscuro sobre fondo oscuro).
- [ ] "Por verificar" con estilo `.info`; borrador vacío con `.empty`.
- [ ] Misma lógica, mismos textos, sin `DuplicateWidgetID`.
- [ ] Sin navegación nueva ni pestañas.
