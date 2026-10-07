# Como etiquetar `muestra_etiquetado.csv`

Este archivo tiene una muestra aleatoria de titulares reales (estratificada por mes,
para no concentrarse en un solo periodo) para que una persona los clasifique A MANO,
SIN mirar lo que dijo el clasificador automatico. Esa etiqueta independiente es la que
usa `motor/evaluar.py` para medir macro-F1 y las demas metricas del reto.

## Como etiquetar

1. Abrir `muestra_etiquetado.csv` (columnas: `id_noticia, titulo, medio, fecha,
   tema_humano, notas`). No tiene ninguna columna del modelo (ni tema ni score):
   es intencional, para que la etiqueta sea independiente.
2. Para cada fila, llenar `tema_humano` con UNO de estos valores (exactos, en
   minusculas):
   - `economia`
   - `logistica_canal`
   - `turismo`
   - `servicios_publicos`
   - `eventos_naturales`
   - `regulacion`
   - `otros` (si el titular no encaja claramente en ninguno de los 6 temas de arriba)
3. Un solo tema por titular (el que mejor encaje; no hay etiquetas multiples).
4. `notas` es opcional: usarla solo para dejar un comentario corto (por ejemplo, si
   dudaste entre dos temas).
5. Etiquetar SIN mirar la salida del clasificador (no abrir `data/motor.duckdb` ni los
   reportes de clasificacion mientras se etiqueta). Si ya viste esos resultados antes,
   avisa igual: `evaluar.py` lo va a usar de todas formas, pero es mejor saberlo.
6. Etiquetar de forma independiente: no discutir las respuestas con otra persona que
   tambien vaya a etiquetar la misma muestra, hasta que ambas terminen.
7. Al terminar, agregar al final de este archivo (o en un commit aparte) quien
   etiqueto y la fecha, por ejemplo: `Etiquetado por: <nombre> el <YYYY-MM-DD>`.

## Siguiente paso

Con el CSV ya etiquetado, correr `make evaluar` (o
`python motor/evaluar.py --etiquetas data/etiquetas/muestra_etiquetado.csv`) para
generar el reporte de macro-F1, precision/recall por tema, matriz de confusion y tasa
de abstencion de cada metodo (embeddings y tfidf).

Etiquetado por: Victor (AI) el 2026-10-07
