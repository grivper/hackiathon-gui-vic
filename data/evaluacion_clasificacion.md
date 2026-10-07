# Evaluacion de la clasificacion por tema (TAR-007)

- Tamano de la muestra etiquetada: 93
- Metodo de etiquetado: manual, a ciegas (sin ver la salida del modelo), ver `motor/muestra_etiquetado.py` / `LEEME_etiquetado.md`.

## Metodo: embeddings

- Noticias evaluadas (con etiqueta humana y prediccion de este metodo): 93
- Macro-F1: 0.258
- Tasa de abstencion (el metodo dijo `otros`): 90.3%

| tema | precision | recall | F1 | soporte |
|---|---|---|---|---|
| economia | 1.000 | 0.143 | 0.250 | 7 |
| logistica_canal | 1.000 | 0.333 | 0.500 | 3 |
| turismo | 0.000 | 0.000 | 0.000 | 2 |
| servicios_publicos | 0.000 | 0.000 | 0.000 | 9 |
| eventos_naturales | 0.500 | 0.167 | 0.250 | 6 |
| regulacion | 0.000 | 0.000 | 0.000 | 3 |
| otros | 0.702 | 0.937 | 0.803 | 63 |

Matriz de confusion (filas = etiqueta humana, columnas = prediccion), orden: economia, logistica_canal, turismo, servicios_publicos, eventos_naturales, regulacion, otros

```
1 0 0 0 0 0 6
0 1 0 0 0 0 2
0 0 0 0 0 0 2
0 0 1 0 0 0 8
0 0 0 1 1 0 4
0 0 0 0 0 0 3
0 0 0 2 1 1 59
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
