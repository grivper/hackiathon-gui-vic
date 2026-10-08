# Riesgos y ética

## Privacidad y Seguridad
Todo el motor, LLM (Ollama con Gemma 3 4B) y la interfaz funcionan 100% offline. No se filtran datos confidenciales, borradores inéditos ni métricas editoriales a la nube pública. No se almacenan datos personales innecesarios ni perfiles de personas.

## Derechos de Autor
La ingesta se limita a metadatos de TVN y GDELT. No se redistribuyen textos completos de artículos, imágenes ni videos, respetando el fair-use y las políticas de la plataforma.

## Sesgos
- **Sesgo de entrenamiento:** Mitigado al restringir el LLM a un modo 100% extractivo (RAG). El modelo redacta basándose estrictamente en las fuentes inyectadas.
- **Sesgo de cobertura:** Las fuentes públicas pueden sobredimensionar la agenda del momento. Mitigado al inyectar contexto oficial (datos demográficos del Banco Mundial y eventos sísmicos del USGS) para proporcionar una línea base objetiva, independiente del volumen de las noticias.

## Ataques al Agente (Prompt Injection)
El texto proveniente de fuentes públicas de internet se trata estrictamente como dato, nunca como instrucción. El sistema superó la prueba del canario malicioso (Prueba T07), demostrando que ignora instrucciones de inyección en titulares falsos.

## Controles Editoriales (El humano en el centro)
- **Estados de revisión:** Las notas recorren 5 estados obligatorios (nuevo, en revisión, requiere evidencia, aprobado como borrador, descartado).
- **Validador de citas estricto:** El código fuente (no el modelo) verifica que cada afirmación provenga de un ID existente. Se descarta automáticamente toda afirmación sin evidencia verificable.
- **Protección de publicación:** El sistema disocia "Puntaje de atención" de "Suficiencia de evidencia". Un tema puede ser altamente viral, pero si no hay pruebas, la interfaz prohíbe la publicación y alerta "Requiere investigación".
- Credenciales fuera del código y de Notion.

## Fuera de alcance
Auditar la verdad absoluta o falsedad última de las noticias, crear perfiles de personas, saltar muros de pago (paywalls).
