# Presentación al jurado (Guion y Estructura)

> **Duración estimada:** 10 minutos (3 minutos de Pitch + 7 de Demo/Arquitectura).

## 1. El Gancho y el Problema (1 min)
*   **Apertura:** "Imaginen llegar a la redacción y tener miles de alertas acumuladas. Un periodista promedio tarda unos 20 minutos solo en cruzar cables, eliminar duplicados y verificar si una noticia de última hora tiene contexto histórico."
*   **El dolor:** "Son 20 minutos operativos donde el periodista no está investigando. Para TVN Media, donde el tiempo es oro y la reputación lo es todo, esto es insostenible y riesgoso: que un tema se repita mucho no significa que esté verificado."

## 2. La Solución y el Valor (1 min)
*   **La herramienta:** "Desarrollamos una **Bandeja Editorial** impulsada por IA local y RAG. El motor clasifica y agrupa los cables de forma automática, y los cruza con contexto oficial (ej. indicadores del Banco Mundial o eventos del USGS)."
*   **La métrica (El Aha! moment):** "El resultado: el periodista obtiene un borrador 100% extractivo y con citas exactas a la fuente original. Lo que tomaba 20 minutos a mano, se resuelve en **1.5 minutos**. Una **reducción del tiempo operativo del 93%**."

## 3. Demo en vivo (4 min)
*   *Mostrar la bandeja offline en Streamlit.*
*   *Consultar un grupo con evidencia sólida:* Mostrar cómo las citas responden extractivamente de las fuentes reales.
*   *Consultar un grupo insuficiente:* Mostrar cómo la interfaz bloquea el borrador ("Requiere investigación y no es publicable"), protegiendo la reputación de la marca contra las alucinaciones.

## 4. Arquitectura e IA (2 min)
*   **Stack:** DuckDB para almacenamiento veloz, Gemma 3 4B corriendo localmente con Ollama, y validación estricta por código (no por prompt).
*   **Offline y Privacidad:** Explicar cómo la IA corre sin internet, protegiendo los datos de TVN de nubes públicas de terceros.
*   **Validación:** Mostrar el validador de citas y la mitigación de Prompt Injection (Caso T07 - Canario).

## 5. Riesgos, límites y próximos pasos (2 min)
*   Mencionar que el agente no es un árbitro de la verdad absoluta, es un copiloto de inteligencia informativa.
*   Dejar claro que la decisión final y el pase a publicación en el CMS recae 100% en el periodista. La tecnología asiste, el humano decide.
