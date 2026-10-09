# Rediseño — Expander "Paquete generado y revisión humana"

> Para Claude Code en local. **Solo estilo y orden visual**: no cambies la lógica del botón "Generar borrador con IA", ni el comando `make generar`, ni los textos (solo se reparten en bloques). Diseño de referencia: tablero "Paquete (propuesta)" en https://claude.ai/artifact/HyJwyeDGCu5j5RjZbwbc7D

## Problemas actuales
1. Dos notas grises sueltas ("Información generada…" y "Aprobar el borrador…") que parecen relleno aunque son advertencias.
2. El botón queda pegado al recuadro punteado.
3. La nota del modelo local queda perdida debajo, y `make generar` sale en verde (estilo por defecto de Streamlit).

## Estructura nueva (dentro del `st.expander`)
1. **Aviso ámbar** con las dos frases juntas: la primera en negrita (es la advertencia), la segunda normal. Icono de advertencia.
2. **Tarjeta de estado vacío** (solo si no hay borrador): icono circular + título "Borrador no generado para este grupo" + línea gris "Ejecutar `make generar`" → debajo, **dentro de la misma tarjeta**, el botón "Generar borrador con IA" → línea divisoria → nota del modelo local con icono de candado: "Usa el modelo local (sin enviar datos fuera). Tarda unos 20 segundos y solo genera este grupo."
3. Si ya hay borrador, muéstralo como hoy dentro de una tarjeta blanca; el aviso ámbar se mantiene arriba.

## Código

```python
import streamlit as st

with st.expander("Paquete generado y revisión humana"):
    st.markdown("""
    <div class="aviso">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l10 18H2L12 3z"/><path d="M12 10v5M12 18v.5"/></svg>
      <div><b>Información generada: el borrador no equivale a información verificada ni autoriza publicación.</b>
      <div>Aprobar el borrador no lo publica automáticamente.</div></div>
    </div>""", unsafe_allow_html=True)

    if not hay_borrador:   # usa tu condición actual
        # el contenedor con key permite estilizarlo como tarjeta (Streamlit >= 1.39)
        with st.container(key=f"vacio_{r['id']}"):
            st.markdown("""
            <div class="vacio-head">
              <div class="vacio-ico"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5z"/><path d="M14 3v5h5"/></svg></div>
              <div><div class="vacio-t">Borrador no generado para este grupo</div>
              <div class="vacio-s">Ejecutar <code>make generar</code></div></div>
            </div>""", unsafe_allow_html=True)

            if st.button("Generar borrador con IA", key=f"gen_{r['id']}"):
                ...  # tu lógica actual, sin cambios

            st.markdown("""
            <div class="vacio-nota">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                   stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/></svg>
              <div>Usa el modelo local (sin enviar datos fuera). Tarda unos 20 segundos y solo genera este grupo.</div>
            </div>""", unsafe_allow_html=True)
```

Si tu Streamlit es anterior a 1.39 (no existe `key` en `st.container`), usa `st.container(border=True)` y estiliza `div[data-testid="stVerticalBlockBorderWrapper"]` dentro del expander, o deja la tarjeta como HTML y el botón justo debajo con `margin-top:-8px`.

## CSS

```css
.aviso{display:flex;gap:12px;align-items:flex-start;background:#fbe9bf;color:#4f3800;
  border-radius:12px;padding:14px 16px;font-size:15px;line-height:1.5;margin-bottom:16px}
.aviso svg{flex:none;margin-top:1px}
.aviso div div{margin-top:4px}

/* tarjeta de estado vacío (el contenedor con key vacio_*) */
[class*="st-key-vacio_"]{background:#fff;border:1px dashed #b9b29f;border-radius:14px;padding:24px;gap:18px}
.vacio-head{display:flex;align-items:center;gap:14px}
.vacio-ico{flex:none;width:48px;height:48px;border-radius:50%;background:#ebe7da;color:#3b392f;
  display:flex;align-items:center;justify-content:center}
.vacio-t{font-size:17px;font-weight:600}
.vacio-s{font-size:14px;color:#5a5648;margin-top:3px}
.vacio-s code,.vacio-nota code{background:#ebe7da;color:#15171c;border-radius:6px;padding:2px 6px;font-size:13px}
.vacio-nota{display:flex;gap:10px;align-items:flex-start;border-top:1px solid #e6e1d3;
  padding-top:16px;font-size:14px;line-height:1.5;color:#5a5648}
.vacio-nota svg{flex:none;margin-top:2px}
```

El botón ya hereda `.stButton>button` (negro, píldora, hover carmesí) de `REDISENO_UI.md`. El `code` verde se corrige con las reglas `.vacio-s code`.

## Criterios de aceptación
- [ ] Las dos advertencias están juntas en un aviso ámbar.
- [ ] El estado vacío es una sola tarjeta: título, botón y nota del modelo local.
- [ ] El botón mantiene su lógica; la clave del widget lleva el id del registro.
- [ ] `make generar` ya no se ve en verde.
- [ ] Textos originales intactos.
