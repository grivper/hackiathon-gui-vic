# UI review hardening (stack 018-021)

## Goal
Fix the logic bug and contract mismatches found reviewing app/app.py and app/data.py on top of feat/draft-tar-021, before merging the stack.

## Facts
- `id_caso` in `fichas` equals `grupo_id`. Table `fichas` (id_caso, estado_revision, tipo_respuesta, ficha JSON, generado_en) may not exist yet (needs Ollama, TAR-022). Pipeline protects `estado_revision` on regeneration (motor/generar.py `estados_existentes`).
- Real citations are `{"id_evidencia", "campo"}`; evidence ids are `N-...`. Real `tipo_respuesta`: respuesta | abstencion | contradiccion, plus `motivo_abstencion`.
- Reproduced bug: regenerating a draft keeps "aprobado como borrador" because the selectbox keeps its own key.

## Tasks
- [ ] T1 State bug: regenerating resets the review state (test-first, AppTest)
- [ ] T2 Draft reads real `fichas` (read-only); no ficha -> honest "borrador no generado"; render abstention/contradiction; remove mock draft
- [ ] T3 Citations traceable: show `id_noticia` in evidence detail; render citas as id_evidencia/campo
- [ ] T4 Persist review state to `fichas.estado_revision` (short write connection), keep pipeline protection
- [ ] T5 Chat mock clearly labeled as simulated; citations not fake-real
- [ ] T6 Minor: distinguish evidence error vs no data, SQL aggregates for filter options, None date guard

## Evidence
(pending)
