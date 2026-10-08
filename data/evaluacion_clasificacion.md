# Evaluacion de la clasificacion por tema (TAR-007)

- Tamano de la muestra etiquetada: 93
- Metodo de etiquetado: manual, a ciegas (sin ver la salida del modelo), ver `motor/muestra_etiquetado.py` / `LEEME_etiquetado.md`.

## Metodo: embeddings

- Noticias evaluadas (con etiqueta humana y prediccion de este metodo): 93
- Macro-F1: 0.339
- Tasa de abstencion (el metodo dijo `otros`): 57.0%

| tema | precision | recall | F1 | soporte |
|---|---|---|---|---|
| economia | 0.333 | 0.286 | 0.308 | 7 |
| logistica_canal | 1.000 | 0.667 | 0.800 | 3 |
| turismo | 0.000 | 0.000 | 0.000 | 2 |
| servicios_publicos | 0.200 | 0.222 | 0.211 | 9 |
| eventos_naturales | 0.333 | 0.500 | 0.400 | 6 |
| regulacion | 0.000 | 0.000 | 0.000 | 3 |
| otros | 0.717 | 0.603 | 0.655 | 63 |

Matriz de confusion (filas = etiqueta humana, columnas = prediccion), orden: economia, logistica_canal, turismo, servicios_publicos, eventos_naturales, regulacion, otros

```
2 0 0 2 0 0 3
0 2 0 0 0 1 0
0 0 0 1 0 0 1
0 0 1 2 0 0 6
0 0 0 1 3 0 2
0 0 0 0 0 0 3
4 0 8 4 6 3 38
```

## Metodo: tfidf

- Noticias evaluadas (con etiqueta humana y prediccion de este metodo): 93
- Macro-F1: 0.145
- Tasa de abstencion (el metodo dijo `otros`): 98.9%

| tema | precision | recall | F1 | soporte |
|---|---|---|---|---|
| economia | 0.000 | 0.000 | 0.000 | 7 |
| logistica_canal | 0.000 | 0.000 | 0.000 | 3 |
| turismo | 0.000 | 0.000 | 0.000 | 2 |
| servicios_publicos | 1.000 | 0.111 | 0.200 | 9 |
| eventos_naturales | 0.000 | 0.000 | 0.000 | 6 |
| regulacion | 0.000 | 0.000 | 0.000 | 3 |
| otros | 0.685 | 1.000 | 0.813 | 63 |

Matriz de confusion (filas = etiqueta humana, columnas = prediccion), orden: economia, logistica_canal, turismo, servicios_publicos, eventos_naturales, regulacion, otros

```
0 0 0 0 0 0 7
0 0 0 0 0 0 3
0 0 0 0 0 0 2
0 0 0 1 0 0 8
0 0 0 0 0 0 6
0 0 0 0 0 0 3
0 0 0 0 0 0 63
```
